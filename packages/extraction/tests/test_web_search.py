from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from argus_extraction.web_search import WebSearchClient, WebSearchResult


def _make_response(*, output_text: str, output: list) -> SimpleNamespace:
    return SimpleNamespace(output_text=output_text, output=output)


def _client_with_response(monkeypatch: pytest.MonkeyPatch, response) -> WebSearchClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = WebSearchClient(model="gpt-4.1")
    fake_responses = MagicMock()
    fake_responses.create = AsyncMock(return_value=response)
    client._client = MagicMock()  # type: ignore[attr-defined]
    client._client.responses = fake_responses  # type: ignore[attr-defined]
    return client


@pytest.mark.asyncio
async def test_search_parses_tool_call_and_message_annotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_text = "Reuters reports the central bank held rates."
    snippet = "central bank held rates"
    start = output_text.index(snippet)
    end = start + len(snippet)

    tool_call_item = {
        "type": "web_search_call",
        "search_results": [
            {
                "url": "https://example.com/a",
                "title": "Example A",
                "snippet": "Example A snippet about rates.",
            }
        ],
    }
    message_item = {
        "type": "message",
        "content": [
            {
                "type": "output_text",
                "text": output_text,
                "annotations": [
                    {
                        "type": "url_citation",
                        "url": "https://reuters.com/article",
                        "title": "Reuters: Rates",
                        "start_index": start,
                        "end_index": end,
                    }
                ],
            }
        ],
    }

    response = _make_response(
        output_text=output_text,
        output=[tool_call_item, message_item],
    )
    client = _client_with_response(monkeypatch, response)

    results = await client.search("central bank rates", max_results=5)
    assert len(results) == 2
    urls = [r.url for r in results]
    assert "https://example.com/a" in urls
    assert "https://reuters.com/article" in urls

    # Reuters annotation snippet must come from the cited window.
    reuters = next(r for r in results if r.url == "https://reuters.com/article")
    assert reuters.snippet == snippet
    assert snippet in reuters.text  # raw_text body retains the cited substring

    example = next(r for r in results if r.url == "https://example.com/a")
    assert example.title == "Example A"
    assert "rates" in example.text


@pytest.mark.asyncio
async def test_search_dedups_by_url(monkeypatch: pytest.MonkeyPatch) -> None:
    output_text = "Snippet text"
    response = _make_response(
        output_text=output_text,
        output=[
            {
                "type": "web_search_call",
                "search_results": [
                    {"url": "https://dup.com/x", "title": "Dup", "snippet": "first"},
                    {"url": "https://dup.com/x", "title": "Dup again", "snippet": "second"},
                ],
            }
        ],
    )
    client = _client_with_response(monkeypatch, response)
    results = await client.search("topic")
    assert len(results) == 1
    assert results[0].url == "https://dup.com/x"


@pytest.mark.asyncio
async def test_search_respects_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response(
        output_text="",
        output=[
            {
                "type": "web_search_call",
                "search_results": [
                    {"url": f"https://x.com/{i}", "title": f"t{i}", "snippet": f"s{i}"}
                    for i in range(5)
                ],
            }
        ],
    )
    client = _client_with_response(monkeypatch, response)
    results = await client.search("topic", max_results=2)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_returns_empty_on_sdk_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = WebSearchClient(model="gpt-4.1")
    fake_responses = MagicMock()
    fake_responses.create = AsyncMock(side_effect=RuntimeError("boom"))
    client._client = MagicMock()  # type: ignore[attr-defined]
    client._client.responses = fake_responses  # type: ignore[attr-defined]

    results = await client.search("anything")
    assert results == []


@pytest.mark.asyncio
async def test_search_returns_empty_for_blank_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = WebSearchClient(model="gpt-4.1")
    # _invoke must NOT be called for blank queries.
    client._invoke = AsyncMock(side_effect=AssertionError("should not be called"))  # type: ignore[attr-defined]
    results = await client.search("   ")
    assert results == []


@pytest.mark.asyncio
async def test_websearchresult_has_expected_fields() -> None:
    from datetime import UTC, datetime

    r = WebSearchResult(
        url="https://x.com",
        title="t",
        snippet="s",
        text="t. s",
        fetched_at=datetime.now(UTC),
    )
    assert r.url == "https://x.com"
    assert r.snippet == "s"
    assert r.text == "t. s"
