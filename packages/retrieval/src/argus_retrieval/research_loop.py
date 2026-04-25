"""Research-time retrieval loop with multi-source web augmentation.

The :class:`ResearchLoop` queries the local Qdrant index first, then —
depending on ``mode`` — either supplements (``"augment"``, default) or
falls back (``"fallback"``) to a configurable mix of open web sources:
OpenAI's hosted ``web_search``, Hacker News (Algolia), and Reddit's
public ``.json`` search. Every URL surfaced by any source is funnelled
through the standard ingestion pipeline (normalize -> hash ->
content-hash dedup -> persist :class:`SourceModel` -> embed -> Qdrant
upsert) before any of its spans become retrievable.

This preserves the citation moat: every ``EvidenceRef`` ultimately points
at a verifiable :class:`Source` row whose ``content_hash`` we recorded.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal
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
from argus_retrieval.hn_search import HNSearchTool
from argus_retrieval.hybrid import HybridRetriever
from argus_retrieval.reddit_search import RedditSearchTool
from argus_retrieval.types import RetrievedSpan
from argus_retrieval.vector import VectorIndex
from argus_retrieval.web_search import OpenAISearchTool, WebSearchHit

logger = get_logger(__name__)

_EMBED_TRUNC = 4000
_INDEXED_SPAN_CHARS = 500


class ResearchLoop:
    """Hybrid local-first retrieval with optional multi-source web augment.

    Steps (``mode="augment"``, default):
      1. Query local Qdrant via :class:`HybridRetriever`.
      2. In parallel, call every configured web tool (OpenAI web_search,
         HN Algolia, Reddit). Each returns up to ``web_results_per_source``
         hits.
      3. Dedup hits by URL across sources, then funnel each URL through
         :meth:`_ingest_url` (fetch, normalize, hash, dedup, persist
         :class:`SourceModel`, embed, upsert to Qdrant).
      4. If anything ingested, re-query local; else return the original
         local hits.

    Steps (``mode="fallback"``, legacy):
      1. Query local.
      2. If ``len(local_hits) < min_local_hits`` AND OpenAI web_search is
         configured, call it; ingest its hits; re-query.

    Either way, provenance is preserved: every span the loop returns
    points at a :class:`Source` row whose ``content_hash`` we recorded.
    """

    def __init__(
        self,
        local_retriever: HybridRetriever,
        embedder: Embedder,
        vector_index: VectorIndex,
        web_search: OpenAISearchTool | None = None,
        hn_search: HNSearchTool | None = None,
        reddit_search: RedditSearchTool | None = None,
        min_local_hits: int = 5,
        web_fetch_timeout: float = 15.0,
        mode: Literal["fallback", "augment"] = "augment",
        web_results_per_source: int = 4,
    ) -> None:
        self._local = local_retriever
        self._embedder = embedder
        self._vector = vector_index
        self._web = web_search
        self._hn = hn_search
        self._reddit = reddit_search
        self._min_local_hits = min_local_hits
        self._timeout = web_fetch_timeout
        self._mode = mode
        self._per_source = web_results_per_source
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

        if self._mode == "fallback":
            return await self._run_fallback(
                topic, local_hits, mentioned_entities=mentioned_entities, top_k=top_k
            )
        return await self._run_augment(
            topic, local_hits, mentioned_entities=mentioned_entities, top_k=top_k
        )

    async def _run_fallback(
        self,
        topic: str,
        local_hits: list[RetrievedSpan],
        *,
        mentioned_entities: Sequence[UUID],
        top_k: int,
    ) -> list[RetrievedSpan]:
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

        if ingested == 0:
            return local_hits

        return await self._local.retrieve(
            topic, mentioned_entities=tuple(mentioned_entities), top_k=top_k
        )

    async def _run_augment(
        self,
        topic: str,
        local_hits: list[RetrievedSpan],
        *,
        mentioned_entities: Sequence[UUID],
        top_k: int,
    ) -> list[RetrievedSpan]:
        sources: list[tuple[str, OpenAISearchTool | HNSearchTool | RedditSearchTool]] = []
        if self._web is not None:
            sources.append(("openai", self._web))
        if self._hn is not None:
            sources.append(("hn", self._hn))
        if self._reddit is not None:
            sources.append(("reddit", self._reddit))

        if not sources:
            return local_hits

        results = await asyncio.gather(
            *(tool.search(topic, max_results=self._per_source) for _, tool in sources),
            return_exceptions=True,
        )

        per_source_hits: dict[str, list[WebSearchHit]] = {}
        for (name, _), res in zip(sources, results, strict=True):
            if isinstance(res, BaseException):
                logger.warning(
                    "research_loop_source_failed", source=name, error=str(res)
                )
                per_source_hits[name] = []
                continue
            per_source_hits[name] = list(res)

        # URL-dedup across sources before _ingest_url. Order: openai, hn, reddit.
        seen_urls: set[str] = set()
        ingested_by_source: dict[str, int] = {name: 0 for name, _ in sources}
        web_total = 0
        for name, _ in sources:
            for hit in per_source_hits.get(name, []):
                if not hit.url or hit.url in seen_urls:
                    continue
                seen_urls.add(hit.url)
                web_total += 1
                try:
                    src = await self._ingest_url(hit.url, hint_title=hit.title)
                except Exception as e:
                    logger.warning(
                        "ingest_url_unhandled_error",
                        url=hit.url,
                        source=name,
                        error=str(e),
                    )
                    continue
                if src is not None:
                    ingested_by_source[name] += 1

        ingested = sum(ingested_by_source.values())
        logger.info(
            "research_loop_augmented",
            topic=topic[:200],
            local=len(local_hits),
            web_total=web_total,
            ingested=ingested,
            by_source=ingested_by_source,
        )

        if ingested == 0:
            return local_hits

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
