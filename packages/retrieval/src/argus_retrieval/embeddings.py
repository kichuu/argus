from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

from argus_core.logging import get_logger
from argus_core.settings import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)


class _Backend(Protocol):
    async def embed_one(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class _SentenceTransformersBackend:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._lock = asyncio.Lock()

    async def _ensure(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model
        async with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("loading_embedder", backend="sentence_transformers", model=self._model_name)
                self._model = await asyncio.to_thread(SentenceTransformer, self._model_name)
        assert self._model is not None
        return self._model

    async def embed_one(self, text: str) -> list[float]:
        model = await self._ensure()
        vec = await asyncio.to_thread(model.encode, text, normalize_embeddings=True)
        return [float(x) for x in vec.tolist()]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = await self._ensure()
        arr = await asyncio.to_thread(
            model.encode, texts, normalize_embeddings=True, batch_size=32
        )
        return [[float(x) for x in row] for row in arr.tolist()]


class _OpenAIBackend:
    """OpenAI embeddings via Responses/Embeddings API.

    text-embedding-3-* supports the `dimensions` parameter (Matryoshka
    representation), so we can request 1024-dim vectors that line up with
    the Qdrant collection's DENSE_SIZE without recreating the collection.
    """

    def __init__(self, model: str, dimensions: int) -> None:
        self._model = model
        self._dimensions = dimensions
        self._client = None
        self._lock = asyncio.Lock()

    async def _ensure(self):
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is None:
                from openai import AsyncOpenAI

                settings = get_settings()
                if not settings.openai_api_key:
                    raise RuntimeError(
                        "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is unset"
                    )
                logger.info(
                    "loading_embedder",
                    backend="openai",
                    model=self._model,
                    dimensions=self._dimensions,
                )
                self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

    async def embed_one(self, text: str) -> list[float]:
        client = await self._ensure()
        resp = await client.embeddings.create(
            model=self._model,
            input=text,
            dimensions=self._dimensions,
        )
        return list(resp.data[0].embedding)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = await self._ensure()
        # OpenAI accepts a list under `input`; one round-trip per batch.
        resp = await client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
        )
        # Preserve input order: API guarantees data sorted by `index`.
        ordered = sorted(resp.data, key=lambda d: d.index)
        return [list(d.embedding) for d in ordered]


def _make_backend() -> _Backend:
    settings = get_settings()
    provider = (settings.embedding_provider or "openai").strip().lower()
    if provider == "openai":
        return _OpenAIBackend(
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
        )
    if provider in {"sentence_transformers", "st", "local"}:
        return _SentenceTransformersBackend(settings.embedding_model)
    raise ValueError(f"unknown EMBEDDING_PROVIDER: {provider!r}")


class Embedder:
    """Backend-agnostic embedding wrapper.

    Picks the backend based on settings.embedding_provider at first use.
    Pass `model_name` to force the sentence-transformers backend with a
    specific model (back-compat for callers that already had a model in mind).
    """

    def __init__(self, model_name: str | None = None) -> None:
        if model_name is not None:
            self._backend: _Backend = _SentenceTransformersBackend(model_name)
        else:
            self._backend = _make_backend()

    async def embed_one(self, text: str) -> list[float]:
        return await self._backend.embed_one(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._backend.embed_batch(texts)
