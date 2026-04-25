"""Embeddings via OpenAI's embeddings API.

Defaults to ``text-embedding-3-small`` (1536-dim) — cheap, fast, no model
download. Set ``ARGUS_EMBEDDING_MODEL`` to override (e.g. ``text-embedding-3-large``
for 3072-dim).

Switched from ``BAAI/bge-large-en-v1.5`` via sentence-transformers because:
- HF first-call cold start was ~30s and hit unauthenticated rate limits
- Project policy is OpenAI-only for LLM/embedding work
- OpenAI embeddings ship faster + already depend on the same API key
"""

from __future__ import annotations

from argus_core.logging import get_logger
from argus_core.settings import get_settings
from openai import AsyncOpenAI

logger = get_logger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_one(self, text: str) -> list[float]:
        if not text:
            raise ValueError("embed_one called with empty text")
        resp = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
        )
        return list(resp.data[0].embedding)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # OpenAI embeddings endpoint accepts an array; one round trip.
        resp = await self._client.embeddings.create(
            model=self._model_name,
            input=texts,
        )
        # Items come back in input order.
        return [list(item.embedding) for item in resp.data]
