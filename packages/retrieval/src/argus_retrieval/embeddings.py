from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from argus_core.logging import get_logger
from argus_core.settings import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or get_settings().embedding_model
        self._model: SentenceTransformer | None = None
        self._lock = asyncio.Lock()

    async def _ensure_loaded(self) -> SentenceTransformer:
        if self._model is not None:
            return self._model
        async with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("loading_embedder", model=self._model_name)
                self._model = await asyncio.to_thread(SentenceTransformer, self._model_name)
        assert self._model is not None
        return self._model

    async def embed_one(self, text: str) -> list[float]:
        model = await self._ensure_loaded()
        vec = await asyncio.to_thread(model.encode, text, normalize_embeddings=True)
        return [float(x) for x in vec.tolist()]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = await self._ensure_loaded()
        arr = await asyncio.to_thread(
            model.encode, texts, normalize_embeddings=True, batch_size=32
        )
        return [[float(x) for x in row] for row in arr.tolist()]
