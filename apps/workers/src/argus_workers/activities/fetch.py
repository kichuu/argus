from __future__ import annotations

import hashlib
from typing import Any

from argus_core.db.models import SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import Source
from argus_ingestion.dedup import SimHashDedup
from argus_ingestion.gdelt import GDELTConnector
from argus_ingestion.rss import RSSConnector
from argus_ingestion.store import RawStore
from sqlalchemy import select
from temporalio import activity

logger = get_logger(__name__)


def _connector_for(config: dict[str, Any]):
    kind = (config.get("kind") or "").lower().strip()
    if kind == "rss":
        feed_urls = config.get("feed_urls") or []
        if not feed_urls:
            raise ValueError("rss config requires 'feed_urls'")
        overrides = config.get("trust_tier_overrides") or {}
        return RSSConnector(feed_urls=list(feed_urls), trust_tier_overrides=dict(overrides))
    if kind == "gdelt":
        query = config.get("query")
        if not query:
            raise ValueError("gdelt config requires 'query'")
        return GDELTConnector(
            query=query,
            max_records=int(config.get("max_records", 250)),
            timeout=float(config.get("timeout", 30.0)),
        )
    raise ValueError(f"unknown ingestion kind: {kind!r}")


async def _persist_source(source: Source, raw_store: RawStore) -> str | None:
    """Persist source if new (by content_hash); return id string or None if duplicate."""
    async with session_scope() as session:
        existing = await session.execute(
            select(SourceModel.id).where(SourceModel.content_hash == source.content_hash)
        )
        row = existing.first()
        if row is not None:
            logger.debug("fetch_source.duplicate", content_hash=source.content_hash)
            return None

        await raw_store.put(source.content_hash, source.raw_text.encode("utf-8"))

        model = SourceModel(
            id=source.id,
            url=str(source.url) if source.url is not None else None,
            feed_url=str(source.feed_url) if source.feed_url is not None else None,
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
        session.add(model)
        return str(source.id)


@activity.defn
async def fetch_source(config: dict[str, Any]) -> list[str]:
    connector = _connector_for(config)
    raw_store = RawStore()
    dedup = SimHashDedup()
    max_items = int(config.get("max_items") or 0)

    persisted: list[str] = []
    seen = 0
    async for source in connector.fetch():
        seen += 1
        if dedup.is_near_duplicate(source.raw_text):
            logger.debug("fetch_source.simhash_dup", content_hash=source.content_hash)
            continue
        dedup.add(source.content_hash, source.raw_text)

        try:
            sid = await _persist_source(source, raw_store)
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_source.persist_failed", error=str(exc), title=source.title)
            continue
        if sid is not None:
            persisted.append(sid)
        if max_items and len(persisted) >= max_items:
            break

    logger.info(
        "fetch_source.done",
        kind=config.get("kind"),
        seen=seen,
        persisted=len(persisted),
    )
    return persisted


@activity.defn
async def index_evidence(source_id: str) -> dict[str, Any]:
    """Phase 4 baseline: vector indexing requires live Qdrant + embedder.

    Recorded no-op for now — wire to argus_retrieval.vector + Qdrant when stack is up.
    """
    logger.info("index_evidence.skipped_baseline", source_id=source_id)
    return {"source_id": source_id, "indexed": 0, "skipped": True}


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
