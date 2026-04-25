"""OpenAI-powered live web search for fresh evidence.

This module wraps the Responses API ``web_search`` tool. The Responses payload
shape changes between SDK minor versions, so the parser is intentionally
defensive: it walks ``resp.output`` and accumulates URL citations from both
``web_search_call`` items and ``url_citation`` annotations on message blocks,
then de-dups by URL.

Failures (auth, rate limit, transport, schema drift) are swallowed at warning
level and yield an empty list — the discussion flow always has the existing
hybrid-retrieval / baseline pack as a fallback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import openai
from argus_core.logging import get_logger
from argus_core.settings import get_settings
from pydantic import BaseModel, Field

logger = get_logger(__name__)


class WebSearchResult(BaseModel):
    """One URL surfaced by the OpenAI web_search tool, normalised."""

    url: str
    title: str
    snippet: str = Field(
        description="Cited substring or annotation excerpt — used for the EvidenceRef span."
    )
    text: str = Field(
        description=(
            "Source body we persist into SourceModel.raw_text. Always contains "
            "`snippet` so we can verify char offsets against it."
        )
    )
    fetched_at: datetime


class WebSearchClient:
    """Thin wrapper over OpenAI Responses API + web_search tool."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.default_research_model
        key = api_key or settings.openai_api_key
        self._client = openai.AsyncOpenAI(api_key=key)

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        if not query or not query.strip():
            return []
        prompt = (
            "Use the web_search tool to find recent, reputable news sources "
            f"directly relevant to the following topic and cite each one with a URL.\n\n"
            f"Topic: {query.strip()}"
        )

        try:
            resp = await self._invoke(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("web_search.invoke_failed", query=query, error=str(exc))
            return []

        try:
            results = self._parse_response(resp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("web_search.parse_failed", query=query, error=str(exc))
            return []

        # De-duplicate by URL while preserving order.
        seen: set[str] = set()
        deduped: list[WebSearchResult] = []
        for r in results:
            if not r.url or r.url in seen:
                continue
            seen.add(r.url)
            deduped.append(r)
            if len(deduped) >= max_results:
                break

        logger.info(
            "web_search.done",
            query=query,
            results=len(deduped),
            model=self._model,
        )
        return deduped

    # --- internals ---------------------------------------------------------

    async def _invoke(self, prompt: str) -> Any:
        responses = getattr(self._client, "responses", None)
        if responses is None or not hasattr(responses, "create"):
            raise RuntimeError("openai SDK lacks Responses API")
        kwargs: dict[str, Any] = {
            "model": self._model,
            "input": prompt,
            "tools": [{"type": "web_search_preview"}],
        }
        try:
            return await responses.create(
                **kwargs,
                tool_choice={"type": "web_search_preview"},
            )
        except TypeError:
            # Older SDKs may not accept tool_choice for this tool.
            return await responses.create(**kwargs)
        except Exception as exc:
            # Some SDKs reject the tool_choice with a generic openai error;
            # retry once without it before bubbling up.
            err_text = str(exc).lower()
            if "tool_choice" in err_text:
                return await responses.create(**kwargs)
            raise

    def _parse_response(self, resp: Any) -> list[WebSearchResult]:
        output_text = self._coerce_str(getattr(resp, "output_text", "") or "")
        output_items = list(getattr(resp, "output", None) or [])

        rows: list[WebSearchResult] = []
        now = datetime.now(UTC)

        for item in output_items:
            kind = self._field(item, "type") or ""
            if kind == "web_search_call":
                rows.extend(self._results_from_search_call(item, now))
            elif kind == "message":
                rows.extend(self._results_from_message(item, output_text, now))
            else:
                # Some SDK versions surface annotations on items without a
                # documented type — try the message path defensively.
                rows.extend(self._results_from_message(item, output_text, now))
        return rows

    def _results_from_search_call(
        self, item: Any, now: datetime
    ) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        # Different SDK versions place results under varying keys.
        candidates = (
            self._field(item, "search_results")
            or self._field(item, "results")
            or []
        )
        # Sometimes results are nested under `action` / `web_search`.
        if not candidates:
            action = self._field(item, "action") or self._field(item, "web_search")
            if action is not None:
                candidates = (
                    self._field(action, "search_results")
                    or self._field(action, "results")
                    or []
                )
        for raw in candidates or []:
            url = self._coerce_str(self._field(raw, "url"))
            if not url:
                continue
            title = self._coerce_str(self._field(raw, "title")) or _host_of(url)
            snippet = self._coerce_str(
                self._field(raw, "snippet")
                or self._field(raw, "text")
                or self._field(raw, "summary")
                or ""
            )
            text = _build_text(title, snippet)
            results.append(
                WebSearchResult(
                    url=url,
                    title=title,
                    snippet=snippet or title,
                    text=text,
                    fetched_at=now,
                )
            )
        return results

    def _results_from_message(
        self, item: Any, output_text: str, now: datetime
    ) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        contents = self._field(item, "content") or []
        for block in contents or []:
            block_text = self._coerce_str(
                self._field(block, "text")
                or self._field(block, "value")
                or ""
            )
            annotations = self._field(block, "annotations") or []
            for ann in annotations:
                ann_type = self._field(ann, "type") or ""
                if "url" not in ann_type and "citation" not in ann_type:
                    # Some SDKs name it `url_citation`, others `citation`.
                    if not self._field(ann, "url"):
                        continue
                url = self._coerce_str(self._field(ann, "url"))
                if not url:
                    continue
                title = (
                    self._coerce_str(self._field(ann, "title"))
                    or _host_of(url)
                )
                start = _coerce_int(self._field(ann, "start_index"))
                end = _coerce_int(self._field(ann, "end_index"))
                snippet = ""
                if (
                    block_text
                    and start is not None
                    and end is not None
                    and 0 <= start < end <= len(block_text)
                ):
                    snippet = block_text[start:end]
                elif (
                    output_text
                    and start is not None
                    and end is not None
                    and 0 <= start < end <= len(output_text)
                ):
                    snippet = output_text[start:end]
                if not snippet:
                    snippet = (
                        self._coerce_str(self._field(ann, "text"))
                        or self._coerce_str(self._field(ann, "quote"))
                        or title
                    )
                text = _build_text(title, snippet, block_text or output_text)
                results.append(
                    WebSearchResult(
                        url=url,
                        title=title,
                        snippet=snippet or title,
                        text=text,
                        fetched_at=now,
                    )
                )
        return results

    @staticmethod
    def _field(obj: Any, name: str) -> Any:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)


def _host_of(url: str) -> str:
    try:
        host = urlparse(url).hostname or url
    except Exception:  # noqa: BLE001
        return url
    return host.removeprefix("www.")


def _build_text(title: str, snippet: str, surrounding: str = "") -> str:
    """Compose SourceModel.raw_text body. Must contain `snippet` verbatim so
    EvidenceRef offsets verify cleanly."""
    title = title or ""
    snippet = snippet or ""
    base = title.strip()
    if snippet and snippet not in base:
        base = f"{base}. {snippet}" if base else snippet
    if surrounding and snippet and snippet in surrounding:
        # Prefer the wider paragraph if it actually contains the snippet.
        if len(surrounding) > len(base):
            return surrounding
    return base or surrounding


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
