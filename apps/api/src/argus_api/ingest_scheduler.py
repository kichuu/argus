"""In-process feed-roster scheduler.

Runs the curated `config/feeds.yaml` roster on a fixed cadence (default 5 min)
as a background asyncio task that lives for the lifetime of the FastAPI app.
No external scheduler, no cron, no launchd — start the API and ingestion
runs.

Disable by setting ``ARGUS_INGEST_ENABLED=false`` in `.env` (e.g., during
dev or tests).

Drift correction: next tick = ``start_wallclock + interval * iteration_index``,
not ``now + interval``, so a slow ingest doesn't push the schedule.

We invoke `scripts/ingest_roster.py` as a subprocess so a crashed pass
doesn't take down the API process.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from argus_core.logging import get_logger
from argus_core.settings import get_settings

logger = get_logger(__name__)


def _repo_root() -> Path:
    """apps/api/src/argus_api/ingest_scheduler.py -> repo root."""
    return Path(__file__).resolve().parents[4]


async def _run_one_pass(repo_root: Path, max_items: int) -> tuple[int, int]:
    """Run `scripts/ingest_roster.py --max-items-override N` as a subprocess.

    Returns (exit_code, stdout_line_count).
    """
    cmd = [
        "uv",
        "run",
        "python",
        "scripts/ingest_roster.py",
        "--max-items-override",
        str(max_items),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(repo_root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    rc = proc.returncode if proc.returncode is not None else -1
    if rc != 0:
        logger.warning(
            "ingest_scheduler.pass_failed",
            exit_code=rc,
            stderr_tail=(stderr_b.decode("utf-8", "replace").splitlines() or [""])[-3:],
        )
    n_lines = len(stdout_b.decode("utf-8", "replace").splitlines())
    return rc, n_lines


async def _scheduler_loop(stop: asyncio.Event) -> None:
    settings = get_settings()
    repo_root = _repo_root()
    interval = settings.ingest_interval_seconds
    max_items = settings.ingest_max_items_per_feed

    feeds_path = repo_root / settings.ingest_feeds_path
    if not feeds_path.exists():
        logger.warning(
            "ingest_scheduler.no_feeds_yaml",
            path=str(feeds_path),
        )
        return

    start_wall = datetime.now(UTC).timestamp()
    iteration = 0

    logger.info(
        "ingest_scheduler.started",
        interval_seconds=interval,
        max_items_per_feed=max_items,
        feeds_yaml=str(feeds_path),
    )

    while not stop.is_set():
        # Drift-corrected next tick.
        next_wall = start_wall + interval * (iteration + 1)
        try:
            t0 = asyncio.get_event_loop().time()
            rc, lines = await _run_one_pass(repo_root, max_items)
            elapsed = asyncio.get_event_loop().time() - t0
            logger.info(
                "ingest_scheduler.tick_done",
                iteration=iteration,
                exit_code=rc,
                elapsed_seconds=round(elapsed, 2),
                stdout_lines=lines,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("ingest_scheduler.tick_unhandled", error=str(exc))

        iteration += 1
        # Sleep until next tick or stop event, whichever first. Slice into
        # short waits so SIGTERM is responsive.
        while not stop.is_set():
            now = datetime.now(UTC).timestamp()
            remaining = next_wall - now
            if remaining <= 0:
                if remaining < -interval:
                    logger.warning(
                        "ingest_scheduler.behind_schedule",
                        seconds_behind=round(-remaining, 1),
                    )
                break
            try:
                await asyncio.wait_for(stop.wait(), timeout=min(remaining, 1.0))
                return  # stop event fired
            except asyncio.TimeoutError:
                continue


class IngestScheduler:
    """Lifecycle wrapper around the loop. start() during FastAPI startup,
    stop() during shutdown."""

    def __init__(self) -> None:
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running():
            return
        self._stop.clear()
        self._task = asyncio.create_task(_scheduler_loop(self._stop))

    async def stop(self) -> None:
        if not self.is_running():
            return
        self._stop.set()
        try:
            assert self._task is not None
            await asyncio.wait_for(self._task, timeout=10.0)
        except asyncio.TimeoutError:
            assert self._task is not None
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        finally:
            self._task = None


_scheduler: IngestScheduler | None = None


def get_scheduler() -> IngestScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = IngestScheduler()
    return _scheduler


async def maybe_start_scheduler() -> None:
    """Honor the ARGUS_INGEST_ENABLED flag; skip in test/dev envs that opt out."""
    settings = get_settings()
    # Allow an explicit env override that beats the settings default. Useful
    # in pytest where we don't want a background loop firing.
    env_override = os.environ.get("ARGUS_INGEST_ENABLED")
    enabled = (
        env_override.lower() in {"1", "true", "yes"}
        if env_override is not None
        else settings.ingest_enabled
    )
    if not enabled:
        logger.info("ingest_scheduler.disabled_by_setting")
        return
    if "pytest" in sys.modules:
        logger.info("ingest_scheduler.disabled_in_pytest")
        return
    await get_scheduler().start()
