from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID

from argus_core.logging import get_logger

from argus_retrieval.embeddings import Embedder
from argus_retrieval.graph import GraphQuerier
from argus_retrieval.rerank import Reranker
from argus_retrieval.types import RetrievedSpan
from argus_retrieval.vector import VectorIndex

logger = get_logger(__name__)

PREFETCH_K = 50
RECENCY_DECAY = 0.05  # per-day exponential decay


class HybridRetriever:
    def __init__(
        self,
        vector_index: VectorIndex,
        graph: GraphQuerier,
        reranker: Reranker,
        embedder: Embedder,
    ) -> None:
        self._vec = vector_index
        self._graph = graph
        self._reranker = reranker
        self._embedder = embedder

    async def _expand_entities(self, mentioned: Sequence[UUID]) -> list[UUID]:
        seen: set[UUID] = set(mentioned)
        for eid in mentioned:
            try:
                hop = await self._graph.neighbors(eid, hops=1, limit=PREFETCH_K)
            except Exception as e:
                logger.warning("neighbor_expansion_failed", entity_id=str(eid), error=str(e))
                continue
            seen.update(hop)
        return list(seen)

    @staticmethod
    def _apply_recency(spans: Iterable[RetrievedSpan]) -> list[RetrievedSpan]:
        now = datetime.now(UTC)
        out: list[RetrievedSpan] = []
        for s in spans:
            fetched = s.fetched_at if s.fetched_at.tzinfo else s.fetched_at.replace(tzinfo=UTC)
            age_days = max(0.0, (now - fetched).total_seconds() / 86400.0)
            weight = math.exp(-age_days * RECENCY_DECAY)
            out.append(s.model_copy(update={"score": s.score * weight}))
        return out

    async def retrieve(
        self,
        query: str,
        mentioned_entities: Sequence[UUID] = (),
        top_k: int = 10,
        recency_boost: bool = True,
    ) -> list[RetrievedSpan]:
        entity_filter: list[UUID] | None = None
        if mentioned_entities:
            entity_filter = await self._expand_entities(mentioned_entities)
            if not entity_filter:
                entity_filter = list(mentioned_entities)

        query_vec = await self._embedder.embed_one(query)

        candidates = await self._vec.search_dense(
            query_vec, top_k=PREFETCH_K, entity_filter=entity_filter
        )

        if recency_boost:
            candidates = self._apply_recency(candidates)
            candidates.sort(key=lambda s: s.score, reverse=True)

        return await self._reranker.rerank(query, candidates, top_k=top_k)
