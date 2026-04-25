from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from argus_retrieval.hn_search import HNSearchTool
from argus_retrieval.web_search import WebSearchHit


def _build_async_client_mock(mocker, response: Any) -> MagicMock:
    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=None)
    factory = mocker.patch("argus_retrieval.hn_search.httpx.AsyncClient")
    factory.return_value = client_instance
    return client_instance


def _resp(payload: Any) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock(return_value=None)
    response.json = MagicMock(return_value=payload)
    return response


@pytest.mark.asyncio
async def test_search_parses_algolia_hits(mocker) -> None:
    payload = {
        "hits": [
            {
                "url": "https://example.com/a",
                "title": "Story A",
                "story_text": "Body A",
                "points": 100,
                "num_comments": 30,
            },
            {
                "url": "https://example.com/b",
                "title": "Story B",
                "story_text": "",
                "points": 5,
                "num_comments": 1,
            },
        ]
    }
    _build_async_client_mock(mocker, _resp(payload))

    tool = HNSearchTool()
    hits = await tool.search("query", max_results=5)

    assert hits == [
        WebSearchHit(url="https://example.com/a", title="Story A", snippet="Body A"),
        WebSearchHit(url="https://example.com/b", title="Story B", snippet=""),
    ]


@pytest.mark.asyncio
async def test_search_skips_hits_without_url(mocker) -> None:
    payload = {
        "hits": [
            {"url": None, "title": "Ask HN: question?", "story_text": "self"},
            {"title": "no-url field", "story_text": "x"},
            {"url": "https://example.com/keep", "title": "Keep", "story_text": "k"},
        ]
    }
    _build_async_client_mock(mocker, _resp(payload))

    tool = HNSearchTool()
    hits = await tool.search("query")

    assert hits == [
        WebSearchHit(url="https://example.com/keep", title="Keep", snippet="k")
    ]


@pytest.mark.asyncio
async def test_search_dedupes_repeated_urls(mocker) -> None:
    payload = {
        "hits": [
            {"url": "https://example.com/x", "title": "t1", "story_text": "s1"},
            {"url": "https://example.com/x", "title": "t2", "story_text": "s2"},
        ]
    }
    _build_async_client_mock(mocker, _resp(payload))

    tool = HNSearchTool()
    hits = await tool.search("query")

    assert len(hits) == 1
    assert hits[0].url == "https://example.com/x"


@pytest.mark.asyncio
async def test_search_respects_max_results(mocker) -> None:
    payload = {
        "hits": [
            {"url": f"https://example.com/{i}", "title": f"t{i}", "story_text": "s"}
            for i in range(10)
        ]
    }
    _build_async_client_mock(mocker, _resp(payload))

    tool = HNSearchTool()
    hits = await tool.search("query", max_results=3)

    assert len(hits) == 3


@pytest.mark.asyncio
async def test_search_returns_empty_on_blank_query(mocker) -> None:
    factory = mocker.patch("argus_retrieval.hn_search.httpx.AsyncClient")

    tool = HNSearchTool()
    hits = await tool.search("   ")

    assert hits == []
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_search_returns_empty_on_http_error(mocker) -> None:
    client_instance = MagicMock()
    client_instance.get = AsyncMock(side_effect=RuntimeError("boom"))
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=None)
    factory = mocker.patch("argus_retrieval.hn_search.httpx.AsyncClient")
    factory.return_value = client_instance

    tool = HNSearchTool()
    hits = await tool.search("query")

    assert hits == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_non_dict_payload(mocker) -> None:
    _build_async_client_mock(mocker, _resp([1, 2, 3]))

    tool = HNSearchTool()
    hits = await tool.search("query")

    assert hits == []
