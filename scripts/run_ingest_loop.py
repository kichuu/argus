"""Argus scheduled ingest loop (foreground daemon).

Runs ``scripts/ingest_roster.py`` on a fixed cadence (default: every
5 minutes) by spawning it as an isolated subprocess. The loop itself
holds no ingestion state — if a single iteration crashes, the next
tick still fires.

    uv run python scripts/run_ingest_loop.py
    uv run python scripts/run_ingest_loop.py --once
    uv run python scripts/run_ingest_loop.py --interval-seconds 300 --max-items-override 3

Why a 5-minute interval?
------------------------
The curated roster in ``config/feeds.yaml`` is 14 free RSS feeds:
gov press rooms (State, Defense, ECB, IMF), wires (Reuters, AP, AFP),
and think-tank publications. Most of these update on a 5-15 minute
cadence; pulling more aggressively wastes our quota and risks IP
throttling. 5 minutes is the floor that keeps us close to wire-time
without being abusive.

Two delivery modes
------------------
1. **Foreground** (this script directly): launch in tmux/screen and
   watch the iteration banners scroll by.
2. **Background** via launchd: see ``scripts/com.argus.ingest.plist``
   and ``scripts/install_ingest_daemon.sh``. We use launchd (not
   cron) because launchd is per-user, restarts on crash via
   ``KeepAlive``, survives logout, and integrates with
   ``launchctl print`` for live introspection. cron on macOS is
   essentially deprecated.

Disabling / debugging
---------------------
* Foreground: Ctrl-C — the SIGINT handler sets a stop flag and the
  loop exits cleanly after the current iteration.
* launchd:    ``./scripts/install_ingest_daemon.sh uninstall``
* Logs:       ``./scripts/install_ingest_daemon.sh logs`` or
              ``~/Library/Logs/argus/ingest-loop.{out,err}.log``

Drift correction
----------------
Each iteration's next-tick is computed from
``start_wallclock + interval * iteration_index``, not from
``now + interval``. A slow iteration therefore does not push later
ticks later — they stay anchored to the original cadence. If a
single ingest exceeds ``interval_seconds``, we log a warning and
start the next iteration immediately rather than queueing.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INGEST_SCRIPT = REPO_ROOT / "scripts" / "ingest_roster.py"
MAX_CAPTURED_LINES = 200  # cap per stream, per iteration


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _drain(stream: asyncio.StreamReader, sink: deque[str]) -> None:
    """Read lines from ``stream`` into ``sink`` (a bounded deque)."""
    while True:
        line = await stream.readline()
        if not line:
            return
        try:
            sink.append(line.decode("utf-8", errors="replace").rstrip("\n"))
        except Exception:
            sink.append("<undecodable line>")


async def _run_once(max_items_override: int | None) -> tuple[int, int, int, float]:
    """Spawn ``ingest_roster.py`` once. Return (exit_code, stdout_lines, stderr_lines, duration_s)."""
    argv: list[str] = [
        sys.executable,
        str(INGEST_SCRIPT),
    ]
    if max_items_override is not None:
        argv.extend(["--max-items-override", str(max_items_override)])

    started = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy(),
    )

    stdout_buf: deque[str] = deque(maxlen=MAX_CAPTURED_LINES)
    stderr_buf: deque[str] = deque(maxlen=MAX_CAPTURED_LINES)

    assert proc.stdout is not None and proc.stderr is not None
    await asyncio.gather(
        _drain(proc.stdout, stdout_buf),
        _drain(proc.stderr, stderr_buf),
    )
    exit_code = await proc.wait()
    duration = time.monotonic() - started

    # Echo the captured tails so the operator can see worker output in the
    # foreground pane / launchd logs.
    if stdout_buf:
        print(f"  --- ingest_roster stdout (last {len(stdout_buf)} lines) ---")
        for line in stdout_buf:
            print(f"  | {line}")
    if stderr_buf:
        print(f"  --- ingest_roster stderr (last {len(stderr_buf)} lines) ---")
        for line in stderr_buf:
            print(f"  ! {line}")

    return exit_code, len(stdout_buf), len(stderr_buf), duration


class _Stop:
    """Mutable stop flag toggled by SIGINT/SIGTERM."""

    def __init__(self) -> None:
        self.flag = False

    def request(self, *_: object) -> None:
        if not self.flag:
            print("\n[argus.ingest] stop signal received; exiting after current iteration")
        self.flag = True


async def _main_async(args: argparse.Namespace) -> int:
    stop = _Stop()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.request)
        except NotImplementedError:
            # Windows / restricted env — fall back to KeyboardInterrupt path.
            pass

    interval = args.interval_seconds
    max_items = args.max_items_override

    if not INGEST_SCRIPT.exists():
        print(f"[argus.ingest] FATAL: cannot find {INGEST_SCRIPT}", file=sys.stderr)
        return 2

    if args.once:
        print(f"[argus.ingest] iter=0 t={_utc_iso(time.time())}  (--once)")
        print(f"  starting: ingest_roster"
              + (f" --max-items-override {max_items}" if max_items is not None else ""))
        exit_code, n_out, n_err, dur = await _run_once(max_items)
        print(f"  duration: {dur:.1f}s   exit={exit_code}   "
              f"stdout_lines={n_out}   stderr_lines={n_err}")
        return exit_code

    start = time.time()
    iteration = 0
    while not stop.flag:
        tick_at = start + interval * iteration
        now = time.time()
        if tick_at > now:
            # Sleep in small slices so the stop flag is checked promptly.
            remaining = tick_at - now
            while remaining > 0 and not stop.flag:
                await asyncio.sleep(min(remaining, 1.0))
                remaining = tick_at - time.time()
            if stop.flag:
                break

        print(f"[argus.ingest] iter={iteration} t={_utc_iso(time.time())}")
        print(f"  starting: ingest_roster"
              + (f" --max-items-override {max_items}" if max_items is not None else ""))

        try:
            exit_code, n_out, n_err, dur = await _run_once(max_items)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"  ERROR: subprocess launch failed: {exc!r}", file=sys.stderr)
            exit_code, n_out, n_err, dur = -1, 0, 0, 0.0

        next_tick = start + interval * (iteration + 1)
        print(f"  duration: {dur:.1f}s   exit={exit_code}   "
              f"stdout_lines={n_out}   stderr_lines={n_err}")

        if dur > interval:
            print(f"  WARN: iteration ran {dur:.1f}s > interval {interval}s; "
                  f"starting next iteration immediately (no queueing)")

        print(f"  next at: {_utc_iso(next_tick)}")
        sys.stdout.flush()
        iteration += 1

    print("[argus.ingest] loop exited cleanly")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the Argus feed roster ingest on a fixed cadence."
    )
    p.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="Seconds between ingest passes (default: 300 = 5 min).",
    )
    p.add_argument(
        "--max-items-override",
        type=int,
        default=None,
        help="Cap items per feed for this loop (forwarded to ingest_roster.py).",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run one ingest pass and exit. Useful for smoke-testing the launchd path.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        return asyncio.run(_main_async(args))
    except KeyboardInterrupt:
        print("\n[argus.ingest] interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
