from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from argus_core.logging import get_logger
from argus_core.settings import get_settings
from qdrant_client import AsyncQdrantClient, models

from argus_retrieval.types import RetrievedSpan

logger = get_logger(__name__)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
DENSE_DIM = 1024  # bge-large-en-v1.5


class VectorIndex:
    def __init__(
        self,
        client: AsyncQdrantClient | None = None,
        collection: str | None = None,
        dense_dim: int = DENSE_DIM,
    ) -> None:
        settings = get_settings()
        self._client = client or AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
            check_compatibility=False,
        )
        self._collection = collection or settings.qdrant_collection_evidence
        self._dense_dim = dense_dim
        self._supports_sparse: bool | None = None

    @property
    def client(self) -> AsyncQdrantClient:
        return self._client

    @property
    def collection(self) -> str:
        return self._collection

    async def ensure_collection(self) -> None:
        existing = await self._client.collection_exists(self._collection)
        if existing:
            return
        try:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config={
                    DENSE_VECTOR_NAME: models.VectorParams(
                        size=self._dense_dim, distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    SPARSE_VECTOR_NAME: models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                },
            )
            self._supports_sparse = True
            logger.info("created_collection_with_sparse", collection=self._collection)
        except Exception as e:
            logger.warning(
                "sparse_unsupported_falling_back_to_dense",
                error=str(e),
                collection=self._collection,
            )
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config={
                    DENSE_VECTOR_NAME: models.VectorParams(
                        size=self._dense_dim, distance=models.Distance.COSINE
                    )
                },
            )
            self._supports_sparse = False

    async def upsert_span(
        self,
        span: RetrievedSpan,
        dense_vec: list[float],
        sparse_vec: dict[int, float] | None = None,
        payload_extras: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "verbatim_span": span.verbatim_span,
            "char_start": span.char_start,
            "char_end": span.char_end,
            "source_id": str(span.source_id),
            "fetched_at": span.fetched_at.isoformat(),
            "trust_tier": span.trust_tier,
            "score": span.score,
            "entity_ids": [str(e) for e in span.entity_ids],
        }
        if payload_extras:
            payload.update(payload_extras)

        vector: dict[str, Any] = {DENSE_VECTOR_NAME: dense_vec}
        if sparse_vec and self._supports_sparse is not False:
            vector[SPARSE_VECTOR_NAME] = models.SparseVector(
                indices=list(sparse_vec.keys()), values=list(sparse_vec.values())
            )

        await self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def _entity_filter(self, entity_filter: list[UUID] | None) -> models.Filter | None:
        if not entity_filter:
            return None
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="entity_ids",
                    match=models.MatchAny(any=[str(e) for e in entity_filter]),
                )
            ]
        )

    @staticmethod
    def _hit_to_span(payload: dict[str, Any], score: float) -> RetrievedSpan | None:
        # Tolerate legacy payloads that wrote 'span' instead of 'verbatim_span',
        # and skip any point missing the required fields entirely (returning None
        # so the caller can filter; raising would tank the whole retrieval).
        text = payload.get("verbatim_span") or payload.get("span")
        src = payload.get("source_id")
        if not text or not src:
            return None
        try:
            entity_ids: list[UUID] = []
            for e in payload.get("entity_ids", []) or []:
                try:
                    entity_ids.append(UUID(str(e)))
                except (ValueError, TypeError):
                    # legacy points stored entity_ids as plain names; skip
                    continue
            return RetrievedSpan(
                verbatim_span=text,
                char_start=int(payload.get("char_start", 0)),
                char_end=int(payload.get("char_end", len(text))),
                source_id=UUID(str(src)),
                fetched_at=datetime.fromisoformat(payload["fetched_at"]),
                trust_tier=int(payload.get("trust_tier", 4)),
                score=score,
                entity_ids=entity_ids,
            )
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("vector_payload_skipped", error=str(exc))
            return None

    async def search_dense(
        self,
        query_vec: list[float],
        top_k: int = 50,
        entity_filter: list[UUID] | None = None,
    ) -> list[RetrievedSpan]:
        results = await self._client.query_points(
            collection_name=self._collection,
            query=query_vec,
            using=DENSE_VECTOR_NAME,
            limit=top_k,
            query_filter=self._entity_filter(entity_filter),
            with_payload=True,
        )
        spans = [self._hit_to_span(p.payload or {}, p.score) for p in results.points]
        return [s for s in spans if s is not None]

    async def search_hybrid(
        self,
        query_vec: list[float],
        sparse_query: dict[int, float],
        top_k: int = 50,
        entity_filter: list[UUID] | None = None,
    ) -> list[RetrievedSpan]:
        flt = self._entity_filter(entity_filter)
        try:
            prefetch = [
                models.Prefetch(
                    query=query_vec, using=DENSE_VECTOR_NAME, limit=top_k * 2, filter=flt
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=list(sparse_query.keys()),
                        values=list(sparse_query.values()),
                    ),
                    using=SPARSE_VECTOR_NAME,
                    limit=top_k * 2,
                    filter=flt,
                ),
            ]
            results = await self._client.query_points(
                collection_name=self._collection,
                prefetch=prefetch,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
                with_payload=True,
            )
            return [self._hit_to_span(p.payload or {}, p.score) for p in results.points]
        except Exception as e:
            logger.warning("hybrid_native_failed_falling_back_rrf", error=str(e))
            return await self._rrf_fallback(query_vec, sparse_query, top_k, entity_filter)

    async def _rrf_fallback(
        self,
        query_vec: list[float],
        sparse_query: dict[int, float],
        top_k: int,
        entity_filter: list[UUID] | None,
    ) -> list[RetrievedSpan]:
        dense_hits = await self.search_dense(query_vec, top_k=top_k * 2, entity_filter=entity_filter)
        sparse_hits: list[RetrievedSpan] = []
        try:
            flt = self._entity_filter(entity_filter)
            res = await self._client.query_points(
                collection_name=self._collection,
                query=models.SparseVector(
                    indices=list(sparse_query.keys()), values=list(sparse_query.values())
                ),
                using=SPARSE_VECTOR_NAME,
                limit=top_k * 2,
                query_filter=flt,
                with_payload=True,
            )
            sparse_hits = [self._hit_to_span(p.payload or {}, p.score) for p in res.points]
        except Exception as e:
            logger.warning("sparse_search_failed_dense_only", error=str(e))

        return _rrf_merge(dense_hits, sparse_hits, top_k=top_k)


def _rrf_merge(
    dense: list[RetrievedSpan], sparse: list[RetrievedSpan], top_k: int, k: int = 60
) -> list[RetrievedSpan]:
    scores: dict[tuple[str, int, int], float] = {}
    spans: dict[tuple[str, int, int], RetrievedSpan] = {}
    for rank, hit in enumerate(dense):
        key = (str(hit.source_id), hit.char_start, hit.char_end)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        spans[key] = hit
    for rank, hit in enumerate(sparse):
        key = (str(hit.source_id), hit.char_start, hit.char_end)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        if key not in spans:
            spans[key] = hit
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    out: list[RetrievedSpan] = []
    for key, fused_score in ordered:
        s = spans[key]
        out.append(s.model_copy(update={"score": fused_score}))
    return out
