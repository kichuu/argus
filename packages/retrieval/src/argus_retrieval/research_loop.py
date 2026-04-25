"""Research-time retrieval loop with web-search fallback.

The :class:`ResearchLoop` queries the local Qdrant index first.  If the
index is sparse (fewer than ``min_local_hits`` results), it falls back to
OpenAI's hosted ``web_search`` tool.  Every URL surfaced by web_search is
funnelled through the standard ingestion pipeline (normalize -> hash ->
content-hash dedup -> persist :class:`SourceModel` -> embed -> Qdrant
upsert) before any of its spans become retrievable.

This preserves the citation moat: every ``EvidenceRef`` ultimately points
at a verifiable :class:`Source` row whose ``content_hash`` we recorded.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

import httpx
from argus_core.db.models import SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import Source
from argus_core.settings import get_settings
from argus_core.trust import load_trust_config
from argus_ingestion import compute_content_hash, normalize_text
from bs4 import BeautifulSoup
from sqlalchemy import select

from argus_retrieval.embeddings import Embedder
from argus_retrieval.hybrid import HybridRetriever
from argus_retrieval.types import RetrievedSpan
from argus_retrieval.vector import VectorIndex
from argus_retrieval.web_search import OpenAISearchTool

logger = get_logger(__name__)

_EMBED_TRUNC = 4000
_INDEXED_SPAN_CHARS = 500


class ResearchLoop:
    """Hybrid local-first / web-fallback retrieval with provenance.

    Steps:
      1. Query local Qdrant via :class:`HybridRetriever`.
      2. If hits < ``min_local_hits``, call ``web_search`` to find URLs.
      3. For each URL: fetch via httpx, normalize, hash, dedup, persist
         :class:`SourceModel`, embed, upload to Qdrant. Skip already-indexed
         (by content_hash).
      4. Re-query Qdrant.
      5. Return :class:`RetrievedSpan` tuples (provenance intact).
    """

    def __init__(
        self,
        local_retriever: HybridRetriever,
        embedder: Embedder,
        vector_index: VectorIndex,
        web_search: OpenAISearchTool | None = None,
        min_local_hits: int = 5,
        web_fetch_timeout: float = 15.0,
    ) -> None:
        self._local = local_retriever
        self._embedder = embedder
        self._vector = vector_index
        self._web = web_search
        self._min_local_hits = min_local_hits
        self._timeout = web_fetch_timeout
        self._trust = load_trust_config()
        self._user_agent = get_settings().wikidata_user_agent

    async def retrieve(
        self,
        topic: str,
        mentioned_entities: Sequence[UUID] = (),
        top_k: int = 10,
    ) -> list[RetrievedSpan]:
        local_hits = await self._local.retrieve(
            topic, mentioned_entities=tuple(mentioned_entities), top_k=top_k
        )
        if len(local_hits) >= self._min_local_hits or self._web is None:
            return local_hits

        logger.info(
            "research_loop_web_fallback",
            topic=topic[:200],
            local_hits=len(local_hits),
            min_local_hits=self._min_local_hits,
        )

        web_hits = await self._web.search(topic, max_results=top_k)
        ingested = 0
        for hit in web_hits:
            try:
                src = await self._ingest_url(hit.url, hint_title=hit.title)
            except Exception as e:
                logger.warning("ingest_url_unhandled_error", url=hit.url, error=str(e))
                continue
            if src is not None:
                ingested += 1

        logger.info(
            "research_loop_ingested",
            topic=topic[:200],
            web_hits=len(web_hits),
            ingested=ingested,
        )

        return await self._local.retrieve(
            topic, mentioned_entities=tuple(mentioned_entities), top_k=top_k
        )

    async def _ingest_url(self, url: str, hint_title: str = "") -> Source | None:
        """Fetch ``url``, normalize, dedup, persist, embed, index.

        Returns the new :class:`Source` or ``None`` if the URL was already
        indexed (content_hash collision) or the fetch failed.
        """
        body = await self._fetch(url)
        if not body:
            return None

        title, raw_text = self._extract(body, hint_title)
        if not raw_text:
            logger.debug("ingest_url_empty_after_normalize", url=url)
            return None

        content_hash = compute_content_hash(raw_text)

        async with session_scope() as session:
            existing = await session.execute(
                select(SourceModel.id)
                .where(SourceModel.content_hash == content_hash)
                .limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                logger.debug("ingest_url_already_indexed", url=url, content_hash=content_hash)
                return None

            host = urlparse(url).hostname or ""
            trust_tier = self._trust.tier_for_domain(host)
            now = datetime.now(UTC)

            source = Source(
                url=url,  # type: ignore[arg-type]
                title=title or url,
                content_hash=content_hash,
                raw_text=raw_text,
                fetched_at=now,
                trust_tier=trust_tier,
                publisher=host or None,
            )

            session.add(
                SourceModel(
                    id=source.id,
                    url=str(source.url) if source.url else None,
                    feed_url=None,
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
            )

        await self._embed_and_index(source)
        logger.info(
            "ingest_url_persisted",
            url=url,
            source_id=str(source.id),
            trust_tier=trust_tier,
            length=len(raw_text),
        )
        return source

    async def _fetch(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": self._user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning("ingest_url_fetch_failed", url=url, error=str(e))
            return None

    @staticmethod
    def _extract(body: str, hint_title: str) -> tuple[str, str]:
        try:
            soup = BeautifulSoup(body, "lxml")
        except Exception:
            soup = BeautifulSoup(body, "html.parser")

        title = hint_title or ""
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()

        text = soup.get_text(separator=" ")
        return title, normalize_text(text)

    async def _embed_and_index(self, source: Source) -> None:
        embed_input = source.raw_text[:_EMBED_TRUNC]
        try:
            dense_vec = await self._embedder.embed_one(embed_input)
        except Exception as e:
            logger.warning(
                "ingest_url_embed_failed",
                source_id=str(source.id),
                error=str(e),
            )
            return

        span_text = source.raw_text[:_INDEXED_SPAN_CHARS]
        if not span_text:
            return
        try:
            span = RetrievedSpan(
                verbatim_span=span_text,
                char_start=0,
                char_end=len(span_text),
                source_id=source.id,
                fetched_at=source.fetched_at,
                trust_tier=source.trust_tier,
                score=0.0,
                entity_ids=[],
            )
        except Exception as e:
            logger.warning(
                "ingest_url_span_invalid", source_id=str(source.id), error=str(e)
            )
            return

        try:
            await self._vector.upsert_span(span, dense_vec=dense_vec)
        except Exception as e:
            logger.warning(
                "ingest_url_qdrant_upsert_failed",
                source_id=str(source.id),
                error=str(e),
            )


__all__: list[str] = ["ResearchLoop"]
