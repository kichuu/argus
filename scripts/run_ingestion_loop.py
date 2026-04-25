"""Continuous ingestion loop. Pulls all configured RSS/HN/Reddit/news feeds
on a fixed cadence (default 90s), persists new sources, embeds + uploads
them to Qdrant. Idempotent on content_hash so re-running just adds new
items.

Run alongside the API + frontend:

    uv run python -m scripts.run_ingestion_loop --interval 90

Or fewer items per tick:

    uv run python -m scripts.run_ingestion_loop --interval 60 --max-per-feed 5

Ctrl-C exits cleanly.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
import time
from typing import Any

from argus_core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_ingestion_loop.py")
    parser.add_argument(
        "--interval",
        type=int,
        default=90,
        help="seconds between ingestion ticks (default 90)",
    )
    parser.add_argument(
        "--max-per-feed",
        type=int,
        default=10,
        help="cap entries pulled per feed per tick (default 10)",
    )
    parser.add_argument(
        "--vertical",
        default=None,
        help="only ingest one vertical (default: all)",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="skip Qdrant embedding/upsert; persist Sources only",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="run a single tick and exit (useful for cron / ad-hoc)",
    )
    return parser.parse_args(argv)


async def _one_tick(args: argparse.Namespace) -> dict[str, Any]:
    # Import inside the loop function so a slow import doesn't block startup.
    from scripts.run_ingestion import _parse_args as _ingest_parse_args
    from scripts.run_ingestion import _run as _ingest_run

    sub_argv: list[str] = ["--max-per-feed", str(args.max_per_feed)]
    if args.vertical:
        sub_argv.extend(["--vertical", args.vertical])
    if args.no_embed:
        sub_argv.append("--no-embed")

    sub_args = _ingest_parse_args(sub_argv)
    rc = await _ingest_run(sub_args)
    return {"exit_code": rc}


async def _loop(args: argparse.Namespace) -> int:
    configure_logging()
    logger.info(
        "ingestion_loop.start",
        interval=args.interval,
        max_per_feed=args.max_per_feed,
        vertical=args.vertical,
        embed=not args.no_embed,
    )

    stop_event = asyncio.Event()

    def _handle_signal(sig: int) -> None:
        logger.info("ingestion_loop.signal", sig=sig)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        # Windows doesn't support add_signal_handler; fall back to default behavior.
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(s, _handle_signal, int(s))

    tick = 0
    while not stop_event.is_set():
        tick += 1
        t0 = time.perf_counter()
        try:
            stats = await _one_tick(args)
            logger.info(
                "ingestion_loop.tick",
                tick=tick,
                duration_s=round(time.perf_counter() - t0, 2),
                **stats,
            )
        except Exception as exc:
            logger.exception("ingestion_loop.tick_failed", tick=tick, error=str(exc))

        if args.once:
            break

        # Sleep until next tick OR stop signal — whichever first.
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=args.interval)
        except TimeoutError:
            continue

    logger.info("ingestion_loop.shutdown", ticks=tick)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_loop(args))


if __name__ == "__main__":
    sys.exit(main())
