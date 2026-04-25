"""Seed ingestion CLI for Argus.

Reads ``config/seed_sources.yaml``, pulls feeds via :class:`RSSConnector`,
persists :class:`SourceModel` rows, and (optionally) embeds + upserts to Qdrant.

One-shot, idempotent: skips entries whose ``content_hash`` is already in the
``sources`` table.

Run::

    uv run python -m scripts.run_ingestion --vertical finance --max-per-feed 10
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import yaml
from argus_core.db.models import SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import configure_logging, get_logger
from argus_ingestion import RSSConnector
from argus_retrieval import Embedder, RetrievedSpan, VectorIndex
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select

if TYPE_CHECKING:
    from argus_core.schemas import Source

logger = get_logger(__name__)

DEFAULT_CONFIG = Path("config/seed_sources.yaml")
DEFAULT_MAX_PER_FEED = 25
PREVIEW_CHARS = 500
EMBED_CHARS = 4000


class FeedSpec(BaseModel):
    name: str
    feed_url: HttpUrl
    trust_tier: int = Field(ge=1, le=4)
    tags: list[str] = Field(default_factory=list)


class SeedConfig(BaseModel):
    verticals: dict[str, list[FeedSpec]]

    def feeds_for(self, vertical: str | None) -> list[tuple[str, FeedSpec]]:
        if vertical is None:
            return [(v, f) for v, feeds in self.verticals.items() for f in feeds]
        if vertical not in self.verticals:
            raise KeyError(f"vertical '{vertical}' not present in config")
        return [(vertical, f) for f in self.verticals[vertical]]


class IngestionStats(BaseModel):
    feeds_processed: int = 0
    sources_stored: int = 0
    sources_skipped: int = 0
    embeddings_upserted: int = 0
    errors: int = 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_ingestion.py")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--vertical", type=str, default=None)
    parser.add_argument("--max-per-feed", type=int, default=DEFAULT_MAX_PER_FEED)
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="skip embedding + Qdrant upsert (DB writes still happen)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch + parse only; no DB writes, no embedding",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def load_config(path: Path) -> SeedConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return SeedConfig.model_validate(raw)


async def _content_hash_exists(session, content_hash: str) -> bool:
    stmt = select(SourceModel.id).where(SourceModel.content_hash == content_hash).limit(1)
    result = await session.execute(stmt)
    return result.first() is not None


def _source_to_model(source: Source) -> SourceModel:
    return SourceModel(
        id=source.id,
        url=str(source.url) if source.url else None,
        feed_url=str(source.feed_url) if source.feed_url else None,
        title=source.title,
        content_hash=source.content_hash,
        raw_text=source.raw_text,
        fetched_at=source.fetched_at,
        published_at=source.published_at,
        license=source.license,
        trust_tier=source.trust_tier,
        publisher=source.publisher,
        language=source.language,
    )


def _build_span(source: Source) -> RetrievedSpan:
    end = min(PREVIEW_CHARS, len(source.raw_text))
    return RetrievedSpan(
        verbatim_span=source.raw_text[:end],
        char_start=0,
        char_end=end,
        source_id=source.id,
        fetched_at=source.fetched_at,
        trust_tier=source.trust_tier,
        score=1.0,
    )


def _trust_overrides_for(feed_url: str, trust_tier: int) -> dict[str, int]:
    host = urlparse(feed_url).hostname
    if not host:
        return {}
    return {host: trust_tier}


async def _process_feed(
    vertical: str,
    spec: FeedSpec,
    *,
    max_per_feed: int,
    dry_run: bool,
    embed: bool,
    embedder: Embedder | None,
    vector_index: VectorIndex | None,
    stats: IngestionStats,
) -> None:
    feed_url = str(spec.feed_url)
    log = logger.bind(vertical=vertical, feed=spec.name, feed_url=feed_url)
    log.info("feed.start", trust_tier=spec.trust_tier)

    connector = RSSConnector(
        feed_urls=[feed_url],
        trust_tier_overrides=_trust_overrides_for(feed_url, spec.trust_tier),
    )

    count = 0
    try:
        async for source in connector.fetch():
            if count >= max_per_feed:
                break
            count += 1

            if dry_run:
                log.debug(
                    "feed.dry_run.parsed",
                    title=source.title,
                    content_hash=source.content_hash[:12],
                )
                stats.sources_stored += 1
                continue

            try:
                stored = await _persist_and_index(
                    source,
                    embed=embed,
                    embedder=embedder,
                    vector_index=vector_index,
                    stats=stats,
                )
            except Exception as exc:
                stats.errors += 1
                log.error("feed.entry_failed", title=source.title, error=str(exc))
                continue

            if stored:
                log.debug(
                    "feed.entry_stored",
                    title=source.title,
                    content_hash=source.content_hash[:12],
                )
    except Exception as exc:
        stats.errors += 1
        log.error("feed.fetch_failed", error=str(exc))
    finally:
        stats.feeds_processed += 1
        log.info("feed.done", entries_seen=count)


async def _persist_and_index(
    source: Source,
    *,
    embed: bool,
    embedder: Embedder | None,
    vector_index: VectorIndex | None,
    stats: IngestionStats,
) -> bool:
    async with session_scope() as session:
        if await _content_hash_exists(session, source.content_hash):
            stats.sources_skipped += 1
            return False
        session.add(_source_to_model(source))

    stats.sources_stored += 1

    if embed and embedder is not None and vector_index is not None:
        text = source.raw_text[:EMBED_CHARS]
        if text:
            dense = await embedder.embed_one(text)
            span = _build_span(source)
            await vector_index.upsert_span(span, dense)
            stats.embeddings_upserted += 1
    return True


async def _run(args: argparse.Namespace) -> int:
    if args.verbose:
        import os

        os.environ["LOG_LEVEL"] = "DEBUG"
    configure_logging()

    config = load_config(args.config)
    feeds = config.feeds_for(args.vertical)
    if not feeds:
        logger.warning("ingestion.no_feeds", vertical=args.vertical)
        return 0

    stats = IngestionStats()
    embed = not args.no_embed and not args.dry_run

    embedder: Embedder | None = None
    vector_index: VectorIndex | None = None
    if embed:
        embedder = Embedder()
        vector_index = VectorIndex()
        await vector_index.ensure_collection()

    logger.info(
        "ingestion.start",
        feed_count=len(feeds),
        vertical=args.vertical or "all",
        dry_run=args.dry_run,
        embed=embed,
        max_per_feed=args.max_per_feed,
    )

    for vertical, spec in feeds:
        await _process_feed(
            vertical,
            spec,
            max_per_feed=args.max_per_feed,
            dry_run=args.dry_run,
            embed=embed,
            embedder=embedder,
            vector_index=vector_index,
            stats=stats,
        )

    logger.info("ingestion.done", **stats.model_dump())
    print(
        f"feeds_processed={stats.feeds_processed} "
        f"sources_stored={stats.sources_stored} "
        f"sources_skipped={stats.sources_skipped} "
        f"embeddings_upserted={stats.embeddings_upserted} "
        f"errors={stats.errors}"
    )
    return 0 if stats.errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
