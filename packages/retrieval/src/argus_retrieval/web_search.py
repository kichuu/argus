"""OpenAI hosted web_search wrapper.

Thin async adapter around the OpenAI Responses API ``web_search`` tool.
The exact response schema differs across SDK minor versions, so parsing
walks ``response.output`` defensively and tolerates several known shapes.
If nothing recognisable is found we log and return ``[]`` rather than
raising — callers should treat the absence of hits as a soft signal.
"""

from __future__ import annotations

from typing import Any

import openai
from argus_core.logging import get_logger
from argus_core.settings import get_settings
from pydantic import BaseModel

logger = get_logger(__name__)


class WebSearchHit(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""


class OpenAISearchTool:
    """Async wrapper around OpenAI's hosted ``web_search`` tool."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.default_research_model
        self._api_key = api_key or settings.openai_api_key

    async def search(self, query: str, max_results: int = 8) -> list[WebSearchHit]:
        if not query.strip():
            return []
        try:
            async with openai.AsyncOpenAI(api_key=self._api_key) as client:
                response = await client.responses.create(
                    model=self._model,
                    tools=[{"type": "web_search"}],
                    tool_choice="auto",
                    input=query,
                )
        except Exception as e:
            logger.warning("web_search_call_failed", error=str(e), query=query[:120])
            return []

        hits = self._parse_response(response)
        if not hits:
            logger.warning(
                "web_search_no_hits_or_unrecognised_shape",
                query=query[:120],
                model=self._model,
            )
            return []
        return _dedup_hits(hits)[:max_results]

    @staticmethod
    def _parse_response(response: Any) -> list[WebSearchHit]:
        output = getattr(response, "output", None)
        if output is None and isinstance(response, dict):
            output = response.get("output")
        if not output:
            return []

        hits: list[WebSearchHit] = []
        for item in output:
            hits.extend(_extract_hits_from_item(item))
        return hits


def _extract_hits_from_item(item: Any) -> list[WebSearchHit]:
    """Defensively pull URL/title/snippet tuples from a Responses output item.

    Known shapes:
      * ``type == 'web_search_call'`` with ``results: [{url,title,snippet}, ...]``.
      * ``type == 'message'`` with ``content[].annotations`` of type
        ``url_citation`` carrying ``{url, title}``.
      * ``type == 'web_search_call'`` exposing only ``urls`` (older SDKs).
    """
    item_type = _get_attr(item, "type") or ""
    item_type = str(item_type)

    hits: list[WebSearchHit] = []

    if "web_search" in item_type:
        results = _get_attr(item, "results") or _get_attr(item, "search_results")
        if results:
            for r in results:
                url = _get_attr(r, "url")
                if not url:
                    continue
                hits.append(
                    WebSearchHit(
                        url=str(url),
                        title=str(_get_attr(r, "title") or ""),
                        snippet=str(
                            _get_attr(r, "snippet")
                            or _get_attr(r, "description")
                            or ""
                        ),
                    )
                )
            return hits

        urls = _get_attr(item, "urls")
        if urls:
            for u in urls:
                if isinstance(u, str):
                    hits.append(WebSearchHit(url=u))
                else:
                    url = _get_attr(u, "url")
                    if url:
                        hits.append(
                            WebSearchHit(
                                url=str(url),
                                title=str(_get_attr(u, "title") or ""),
                            )
                        )
            return hits

    if item_type == "message":
        content = _get_attr(item, "content") or []
        for block in content:
            annotations = _get_attr(block, "annotations") or []
            for ann in annotations:
                ann_type = str(_get_attr(ann, "type") or "")
                if "url_citation" not in ann_type and "citation" not in ann_type:
                    continue
                url = _get_attr(ann, "url")
                if not url:
                    continue
                hits.append(
                    WebSearchHit(
                        url=str(url),
                        title=str(_get_attr(ann, "title") or ""),
                        snippet=str(_get_attr(ann, "snippet") or ""),
                    )
                )

    return hits


def _get_attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _dedup_hits(hits: list[WebSearchHit]) -> list[WebSearchHit]:
    seen: set[str] = set()
    out: list[WebSearchHit] = []
    for h in hits:
        if h.url in seen:
            continue
        seen.add(h.url)
        out.append(h)
    return out


__all__ = ["OpenAISearchTool", "WebSearchHit"]
