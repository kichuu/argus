"""Hacker News Algolia search adapter.

Free, no API key required. Endpoint:
``https://hn.algolia.com/api/v1/search?query={q}&tags=story&hitsPerPage={n}``

Each hit carries ``url, title, story_text, points, num_comments, created_at``.
Items without a ``url`` (Ask HN, Show HN self-posts, etc.) are skipped — we
only ingest fetchable links that the :class:`ResearchLoop._ingest_url`
pipeline can normalize, hash, and embed.
"""

from __future__ import annotations

from typing import Any

import httpx
from argus_core.logging import get_logger

from argus_retrieval.web_search import WebSearchHit

logger = get_logger(__name__)


class HNSearchTool:
    """Async wrapper over the HN Algolia ``/search`` endpoint."""

    def __init__(
        self,
        base_url: str = "https://hn.algolia.com/api/v1",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def search(self, query: str, max_results: int = 8) -> list[WebSearchHit]:
        if not query.strip():
            return []

        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": str(max_results),
        }
        url = f"{self._base_url}/search"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as e:
            logger.warning("hn_search_failed", error=str(e), query=query[:120])
            return []

        return _parse_hits(payload, max_results=max_results)


def _parse_hits(payload: Any, *, max_results: int) -> list[WebSearchHit]:
    if not isinstance(payload, dict):
        return []
    raw_hits = payload.get("hits") or []
    if not isinstance(raw_hits, list):
        return []

    out: list[WebSearchHit] = []
    seen: set[str] = set()
    for h in raw_hits:
        if not isinstance(h, dict):
            continue
        url = h.get("url")
        if not url or not isinstance(url, str):
            continue
        if url in seen:
            continue
        seen.add(url)
        title = str(h.get("title") or h.get("story_title") or "")
        snippet = str(h.get("story_text") or "")
        out.append(WebSearchHit(url=url, title=title, snippet=snippet))
        if len(out) >= max_results:
            break
    return out


__all__ = ["HNSearchTool"]
