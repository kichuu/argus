"""Reddit search adapter via the public ``.json`` endpoint.

No auth required for public search; Reddit *does* require a non-blank polite
``User-Agent`` header — empty/default UAs return HTTP 429.

Endpoint: ``https://www.reddit.com/search.json?q={q}&sort=relevance&limit={n}``.
Listing is nested as ``data.children[].data`` with ``url`` (link post) or
``permalink`` (self post — we synthesize the full URL).
"""

from __future__ import annotations

from typing import Any

import httpx
from argus_core.logging import get_logger
from argus_core.settings import get_settings

from argus_retrieval.web_search import WebSearchHit

logger = get_logger(__name__)

_REDDIT_BASE = "https://www.reddit.com"


class RedditSearchTool:
    """Async wrapper over Reddit's public search JSON listing."""

    def __init__(
        self,
        user_agent: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._user_agent = user_agent or get_settings().wikidata_user_agent
        self._timeout = timeout

    async def search(self, query: str, max_results: int = 8) -> list[WebSearchHit]:
        if not query.strip():
            return []

        params = {
            "q": query,
            "sort": "relevance",
            "limit": str(max_results),
        }
        headers = {"User-Agent": self._user_agent}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
                response = await client.get(f"{_REDDIT_BASE}/search.json", params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as e:
            logger.warning("reddit_search_failed", error=str(e), query=query[:120])
            return []

        return _parse_listing(payload, max_results=max_results)


def _parse_listing(payload: Any, *, max_results: int) -> list[WebSearchHit]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    if not isinstance(children, list):
        return []

    out: list[WebSearchHit] = []
    seen: set[str] = set()
    for child in children:
        if not isinstance(child, dict):
            continue
        cdata = child.get("data")
        if not isinstance(cdata, dict):
            continue

        url = cdata.get("url")
        if not isinstance(url, str) or not url:
            permalink = cdata.get("permalink")
            if isinstance(permalink, str) and permalink:
                url = f"{_REDDIT_BASE}{permalink}"
            else:
                continue

        if url in seen:
            continue
        seen.add(url)

        title = str(cdata.get("title") or "")
        snippet = str(cdata.get("selftext") or "")
        out.append(WebSearchHit(url=url, title=title, snippet=snippet))
        if len(out) >= max_results:
            break
    return out


__all__ = ["RedditSearchTool"]
