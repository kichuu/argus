"""Backfill latitude/longitude for entities with a Wikidata Q-ID.

Queries Wikidata SPARQL for property P625 (coordinate location) for each
entity matching ``wikidata_id IS NOT NULL AND latitude IS NULL``. Wikidata
returns the value as a ``Point(lon lat)`` literal which is parsed in place.

Run::

    uv run python -m scripts.geocode_entities --batch 50 --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from typing import TYPE_CHECKING

import httpx
from argus_core.db.models import EntityModel
from argus_core.db.session import session_scope
from argus_core.logging import configure_logging, get_logger
from argus_core.settings import get_settings
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

WIKIDATA_RATE_LIMIT_SECONDS = 1.0
DEFAULT_BATCH = 100
HTTP_TIMEOUT_SECONDS = 30.0

# Matches "Point(<lon> <lat>)"; both numbers may be negative or fractional.
_POINT_RE = re.compile(
    r"^\s*Point\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)\s*$"
)


class GeocodeStats:
    def __init__(self) -> None:
        self.scanned = 0
        self.found = 0
        self.missing = 0
        self.errors = 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="geocode_entities.py")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _parse_point(literal: str) -> tuple[float, float] | None:
    """Parse a Wikidata ``Point(lon lat)`` WKT literal into ``(lat, lon)``."""
    match = _POINT_RE.match(literal)
    if match is None:
        return None
    lon = float(match.group(1))
    lat = float(match.group(2))
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon


def _build_sparql(qid: str) -> str:
    return f"SELECT ?coord WHERE {{ wd:{qid} wdt:P625 ?coord }} LIMIT 1"


async def _fetch_coords(
    client: httpx.AsyncClient, endpoint: str, headers: dict[str, str], qid: str
) -> tuple[float, float] | None:
    sparql = _build_sparql(qid)
    resp = await client.get(
        endpoint,
        params={"query": sparql, "format": "json"},
        headers=headers,
    )
    resp.raise_for_status()
    payload = resp.json()
    bindings = payload.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    value = bindings[0].get("coord", {}).get("value")
    if not value:
        return None
    return _parse_point(value)


async def _select_targets(session: AsyncSession, batch: int) -> list[EntityModel]:
    stmt = (
        select(EntityModel)
        .where(
            EntityModel.wikidata_id.is_not(None),
            EntityModel.latitude.is_(None),
        )
        .order_by(EntityModel.created_at.asc())
        .limit(batch)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _run(args: argparse.Namespace) -> int:
    if args.verbose:
        import os

        os.environ["LOG_LEVEL"] = "DEBUG"
    configure_logging()

    settings = get_settings()
    stats = GeocodeStats()
    headers = {
        "User-Agent": settings.wikidata_user_agent,
        "Accept": "application/sparql-results+json",
    }

    async with session_scope() as session:
        targets = await _select_targets(session, args.batch)
        logger.info(
            "geocode.start",
            batch=args.batch,
            dry_run=args.dry_run,
            target_count=len(targets),
        )

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            for index, entity in enumerate(targets):
                stats.scanned += 1
                qid = entity.wikidata_id or ""
                log = logger.bind(entity_id=str(entity.id), wikidata_id=qid)
                try:
                    coords = await _fetch_coords(
                        client, settings.wikidata_sparql, headers, qid
                    )
                except Exception as exc:
                    stats.errors += 1
                    log.error("geocode.fetch_failed", error=str(exc))
                else:
                    if coords is None:
                        stats.missing += 1
                        log.info("geocode.no_coords")
                    else:
                        lat, lon = coords
                        stats.found += 1
                        log.info("geocode.found", lat=lat, lon=lon)
                        if not args.dry_run:
                            entity.latitude = lat
                            entity.longitude = lon

                # Rate-limit between requests, not after the last.
                if index < len(targets) - 1:
                    await asyncio.sleep(WIKIDATA_RATE_LIMIT_SECONDS)

    logger.info(
        "geocode.done",
        scanned=stats.scanned,
        found=stats.found,
        missing=stats.missing,
        errors=stats.errors,
    )
    print(
        f"scanned={stats.scanned} found={stats.found} "
        f"missing={stats.missing} errors={stats.errors}"
    )
    return 0 if stats.errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
