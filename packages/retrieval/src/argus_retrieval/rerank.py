from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from argus_core.logging import get_logger
from argus_core.settings import get_settings

from argus_retrieval.types import RetrievedSpan

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = get_logger(__name__)


class Reranker(ABC):
    @abstractmethod
    async def rerank(
        self, query: str, candidates: list[RetrievedSpan], top_k: int = 10
    ) -> list[RetrievedSpan]: ...


class CohereReranker(Reranker):
    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None:
        import cohere

        self._client = cohere.AsyncClient(api_key=api_key)
        self._model = model

    async def rerank(
        self, query: str, candidates: list[RetrievedSpan], top_k: int = 10
    ) -> list[RetrievedSpan]:
        if not candidates:
            return []
        docs = [c.verbatim_span for c in candidates]
        try:
            resp = await self._client.rerank(
                model=self._model, query=query, documents=docs, top_n=min(top_k, len(docs))
            )
        except Exception as e:
            logger.warning("cohere_rerank_failed_using_input_order", error=str(e))
            return candidates[:top_k]

        out: list[RetrievedSpan] = []
        for r in resp.results:
            idx = int(r.index)
            score = float(r.relevance_score)
            out.append(candidates[idx].model_copy(update={"score": score}))
        return out


class LocalReranker(Reranker):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().reranker_model
        self._model: CrossEncoder | None = None
        self._lock = asyncio.Lock()

    async def _ensure_loaded(self) -> CrossEncoder:
        if self._model is not None:
            return self._model
        async with self._lock:
            if self._model is None:
                from sentence_transformers import CrossEncoder

                logger.info("loading_local_reranker", model=self._model_name)
                self._model = await asyncio.to_thread(CrossEncoder, self._model_name)
        assert self._model is not None
        return self._model

    async def rerank(
        self, query: str, candidates: list[RetrievedSpan], top_k: int = 10
    ) -> list[RetrievedSpan]:
        if not candidates:
            return []
        model = await self._ensure_loaded()
        pairs = [(query, c.verbatim_span) for c in candidates]
        scores = await asyncio.to_thread(model.predict, pairs)
        scored = list(zip(candidates, [float(s) for s in scores], strict=True))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [c.model_copy(update={"score": s}) for c, s in scored[:top_k]]


class NoOpReranker(Reranker):
    """Returns candidates as-is. Default — skips reranking entirely.

    Local CrossEncoder reranking pulls a 1.1GB model on first use, which
    blocks discussion runs for minutes. Cohere reranker requires an API
    key. NoOp is the right default for dev and small indexes; opt into
    cohere/local via RERANKER_PROVIDER env when you need it.
    """

    async def rerank(
        self, query: str, candidates: list[RetrievedSpan], top_k: int = 10
    ) -> list[RetrievedSpan]:
        return candidates[:top_k]


def get_reranker() -> Reranker:
    settings = get_settings()
    provider = (settings.reranker_provider or "none").strip().lower()
    if provider == "cohere":
        if not settings.cohere_api_key:
            logger.warning("reranker_provider_cohere_no_key_falling_back_to_noop")
            return NoOpReranker()
        return CohereReranker(api_key=settings.cohere_api_key)
    if provider == "local":
        return LocalReranker()
    if provider not in {"none", ""}:
        logger.warning("reranker_provider_unknown_falling_back_to_noop", provider=provider)
    return NoOpReranker()
