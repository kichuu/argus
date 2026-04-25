from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID, uuid4

from argus_core.db.models import ClaimModel, SourceModel
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


async def _load_source_and_claims(
    source_id: str,
) -> tuple[SourceModel | None, list[tuple[ClaimModel, dict[str, Any]]]]:
    """Return the source row plus (claim, evidence_dict) pairs whose evidence
    points at ``source_id``.

    A single claim may have multiple evidence refs into the same source; we
    yield one tuple per (claim, matching evidence) pair so each verbatim span
    becomes its own vector.
    """
    src_uuid = UUID(source_id)
    async with session_scope() as session:
        src_row = await session.get(SourceModel, src_uuid)
        if src_row is None:
            return None, []

        # Postgres JSONB containment: claims whose supporting_evidence array
        # contains an element with this source_id.
        stmt = select(ClaimModel).where(
            ClaimModel.supporting_evidence.contains(
                [{"source_id": str(src_uuid)}]
            )
        )
        result = await session.execute(stmt)
        claims = list(result.scalars().all())

    pairs: list[tuple[ClaimModel, dict[str, Any]]] = []
    for claim in claims:
        for ev in claim.supporting_evidence or []:
            if not isinstance(ev, dict):
                continue
            if str(ev.get("source_id")) == str(src_uuid):
                pairs.append((claim, ev))
    return src_row, pairs


@activity.defn
async def index_evidence(source_id: str) -> dict[str, Any]:
    """Embed each evidence span attached to ``source_id`` and upsert into Qdrant.

    Best-effort: a Qdrant outage does not fail the workflow. Returns a status
    dict with ``indexed`` count and ``skipped`` flag.
    """
    try:
        src_row, pairs = await _load_source_and_claims(source_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("index_evidence.load_failed", source_id=source_id, error=str(exc))
        return {"source_id": source_id, "indexed": 0, "skipped": True, "reason": "load_failed"}

    if src_row is None:
        logger.info("index_evidence.source_missing", source_id=source_id)
        return {"source_id": source_id, "indexed": 0, "skipped": True, "reason": "source_missing"}

    if not pairs:
        logger.info("index_evidence.no_evidence", source_id=source_id)
        return {"source_id": source_id, "indexed": 0, "skipped": False}

    # Lazy imports so the activity module stays importable without these
    # heavy deps (sentence-transformers / qdrant-client) in unit tests.
    try:
        from argus_core.settings import get_settings
        from argus_retrieval.embeddings import Embedder
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.http import models as qm
    except ImportError as exc:
        logger.warning("index_evidence.deps_missing", error=str(exc))
        return {
            "source_id": source_id,
            "indexed": 0,
            "skipped": True,
            "reason": "deps_missing",
        }

    settings = get_settings()
    embedder = Embedder()
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )

    points: list[Any] = []
    try:
        for claim, ev in pairs:
            span_text = str(ev.get("verbatim_span") or "")
            if not span_text:
                continue
            try:
                vec = await embedder.embed_one(span_text)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "index_evidence.embed_failed",
                    claim_id=str(claim.id),
                    error=str(exc),
                )
                continue

            payload: dict[str, Any] = {
                "source_id": str(src_row.id),
                "claim_id": str(claim.id),
                "span": span_text,
                "char_start": int(ev.get("char_start") or 0),
                "char_end": int(ev.get("char_end") or len(span_text)),
                "fetched_at": (
                    src_row.fetched_at.isoformat()
                    if src_row.fetched_at is not None
                    else None
                ),
                "trust_tier": int(
                    ev.get("trust_tier")
                    if ev.get("trust_tier") is not None
                    else src_row.trust_tier
                ),
                "entity_ids": [str(e) for e in (claim.affected_entities or [])],
            }
            points.append(
                qm.PointStruct(
                    id=str(uuid4()),
                    vector={"dense": vec},
                    payload=payload,
                )
            )

        if not points:
            logger.info("index_evidence.no_points", source_id=source_id)
            return {"source_id": source_id, "indexed": 0, "skipped": False}

        try:
            await client.upsert(
                collection_name=settings.qdrant_collection_evidence,
                points=points,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "index_evidence.qdrant_unavailable",
                source_id=source_id,
                error=str(exc),
            )
            return {
                "source_id": source_id,
                "indexed": 0,
                "skipped": True,
                "reason": "qdrant_unavailable",
            }

        logger.info(
            "index_evidence.upserted",
            source_id=source_id,
            indexed=len(points),
        )
        return {"source_id": source_id, "indexed": len(points), "skipped": False}
    finally:
        try:
            await client.close()
        except Exception:  # noqa: BLE001
            pass


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
