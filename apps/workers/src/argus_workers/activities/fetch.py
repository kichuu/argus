"""Temporal activities for ingestion: fetch sources, index evidence.

These wrap the same logic as ``scripts/run_ingestion.py`` but constrained for
Temporal heartbeat budgets. Idempotent on ``content_hash``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from argus_core.db.models import SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import Source
from argus_ingestion import GDELTConnector, RSSConnector, SourceConnector
from argus_retrieval import Embedder, RetrievedSpan, VectorIndex
from sqlalchemy import select
from temporalio import activity

logger = get_logger(__name__)

DEFAULT_MAX_RECORDS = 50
PREVIEW_CHARS = 500
EMBED_CHARS = 4000


def _build_connector(config: dict[str, Any]) -> SourceConnector:
    kind = config.get("kind", "rss")
    if kind == "rss":
        feed_url = config["feed_url"]
        trust_tier = config.get("trust_tier")
        overrides: dict[str, int] = {}
        if trust_tier is not None:
            host = urlparse(feed_url).hostname
            if host:
                overrides[host] = int(trust_tier)
        return RSSConnector(feed_urls=[feed_url], trust_tier_overrides=overrides)
    if kind == "gdelt":
        query = config["query"]
        return GDELTConnector(query=query)
    raise ValueError(f"unsupported connector kind: {kind}")


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


def _build_span(source_id: UUID, raw_text: str, fetched_at, trust_tier: int) -> RetrievedSpan:
    end = min(PREVIEW_CHARS, len(raw_text))
    return RetrievedSpan(
        verbatim_span=raw_text[:end],
        char_start=0,
        char_end=end,
        source_id=source_id,
        fetched_at=fetched_at,
        trust_tier=trust_tier,
        score=1.0,
    )


async def _content_hash_exists(session, content_hash: str) -> bool:
    stmt = select(SourceModel.id).where(SourceModel.content_hash == content_hash).limit(1)
    result = await session.execute(stmt)
    return result.first() is not None


@activity.defn
async def fetch_source(config: dict[str, Any]) -> list[str]:
    """Fetch a single source feed/query, persist new sources, return their IDs.

    ``config`` keys:
        kind: "rss" | "gdelt"
        feed_url: str (rss)
        query: str (gdelt)
        trust_tier: int (optional override for the feed's hostname)
        max_records: int (default 50)
    """
    max_records = int(config.get("max_records", DEFAULT_MAX_RECORDS))
    connector = _build_connector(config)

    persisted_ids: list[str] = []
    seen = 0
    async for source in connector.fetch():
        if seen >= max_records:
            break
        seen += 1
        async with session_scope() as session:
            if await _content_hash_exists(session, source.content_hash):
                logger.debug("fetch_source.skip_duplicate", content_hash=source.content_hash[:12])
                continue
            session.add(_source_to_model(source))
        persisted_ids.append(str(source.id))

    logger.info(
        "fetch_source.done",
        kind=config.get("kind"),
        seen=seen,
        persisted=len(persisted_ids),
    )
    return persisted_ids


@activity.defn
async def index_evidence(source_ids: list[str]) -> dict[str, Any]:
    """Re-embed and upsert sources to Qdrant. Idempotent at the source level."""
    if not source_ids:
        return {"indexed": 0, "skipped": 0}

    embedder = Embedder()
    vector_index = VectorIndex()
    await vector_index.ensure_collection()

    indexed = 0
    skipped = 0
    for sid in source_ids:
        try:
            uuid = UUID(sid)
        except ValueError:
            logger.warning("index_evidence.bad_uuid", source_id=sid)
            skipped += 1
            continue

        async with session_scope() as session:
            row = await session.get(SourceModel, uuid)
        if row is None:
            logger.warning("index_evidence.missing_source", source_id=sid)
            skipped += 1
            continue
        if not row.raw_text:
            skipped += 1
            continue

        text = row.raw_text[:EMBED_CHARS]
        dense = await embedder.embed_one(text)
        span = _build_span(row.id, row.raw_text, row.fetched_at, row.trust_tier)
        await vector_index.upsert_span(span, dense)
        indexed += 1

    logger.info("index_evidence.done", indexed=indexed, skipped=skipped)
    return {"indexed": indexed, "skipped": skipped}
