from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from argus_retrieval.reddit_search import RedditSearchTool
from argus_retrieval.web_search import WebSearchHit


def _resp(payload: Any) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock(return_value=None)
    response.json = MagicMock(return_value=payload)
    return response


def _patch_client(mocker, response: Any) -> tuple[MagicMock, MagicMock]:
    client_instance = MagicMock()
    client_instance.get = AsyncMock(return_value=response)
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=None)
    factory = mocker.patch("argus_retrieval.reddit_search.httpx.AsyncClient")
    factory.return_value = client_instance
    return factory, client_instance


def _listing(children: list[dict[str, Any]]) -> dict[str, Any]:
    return {"data": {"children": [{"kind": "t3", "data": c} for c in children]}}


@pytest.mark.asyncio
async def test_search_parses_link_posts(mocker) -> None:
    payload = _listing(
        [
            {
                "url": "https://example.com/article",
                "permalink": "/r/news/comments/abc/",
                "title": "External link",
                "selftext": "",
            },
            {
                "url": "https://example.com/another",
                "permalink": "/r/news/comments/def/",
                "title": "Another",
                "selftext": "",
            },
        ]
    )
    _patch_client(mocker, _resp(payload))

    tool = RedditSearchTool(user_agent="argus-test/0.1")
    hits = await tool.search("query")

    assert hits == [
        WebSearchHit(url="https://example.com/article", title="External link", snippet=""),
        WebSearchHit(url="https://example.com/another", title="Another", snippet=""),
    ]


@pytest.mark.asyncio
async def test_search_falls_back_to_permalink_for_self_posts(mocker) -> None:
    payload = _listing(
        [
            {
                "url": "",
                "permalink": "/r/news/comments/abc/self_post/",
                "title": "Self post",
                "selftext": "Body",
            },
            {
                "permalink": "/r/news/comments/xyz/no_url/",
                "title": "No url field",
                "selftext": "Body2",
            },
        ]
    )
    _patch_client(mocker, _resp(payload))

    tool = RedditSearchTool(user_agent="argus-test/0.1")
    hits = await tool.search("query")

    assert [h.url for h in hits] == [
        "https://www.reddit.com/r/news/comments/abc/self_post/",
        "https://www.reddit.com/r/news/comments/xyz/no_url/",
    ]
    assert hits[0].snippet == "Body"


@pytest.mark.asyncio
async def test_search_sets_polite_user_agent_header(mocker) -> None:
    factory, _client = _patch_client(mocker, _resp(_listing([])))

    tool = RedditSearchTool(user_agent="argus-test/0.9 (+https://example.com)")
    await tool.search("query")

    factory.assert_called_once()
    kwargs = factory.call_args.kwargs
    assert kwargs.get("headers") == {
        "User-Agent": "argus-test/0.9 (+https://example.com)"
    }


@pytest.mark.asyncio
async def test_search_uses_settings_user_agent_when_not_provided(mocker) -> None:
    fake_settings = MagicMock()
    fake_settings.wikidata_user_agent = "argus-default/0.1"
    mocker.patch(
        "argus_retrieval.reddit_search.get_settings", return_value=fake_settings
    )
    factory, _client = _patch_client(mocker, _resp(_listing([])))

    tool = RedditSearchTool()
    await tool.search("query")

    kwargs = factory.call_args.kwargs
    assert kwargs.get("headers") == {"User-Agent": "argus-default/0.1"}


@pytest.mark.asyncio
async def test_search_returns_empty_on_429(mocker) -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock(side_effect=RuntimeError("429"))
    response.json = MagicMock(return_value={})
    _patch_client(mocker, response)

    tool = RedditSearchTool(user_agent="argus-test/0.1")
    hits = await tool.search("query")

    assert hits == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_transport_error(mocker) -> None:
    client_instance = MagicMock()
    client_instance.get = AsyncMock(side_effect=RuntimeError("boom"))
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=None)
    factory = mocker.patch("argus_retrieval.reddit_search.httpx.AsyncClient")
    factory.return_value = client_instance

    tool = RedditSearchTool(user_agent="argus-test/0.1")
    hits = await tool.search("query")

    assert hits == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_blank_query(mocker) -> None:
    factory = mocker.patch("argus_retrieval.reddit_search.httpx.AsyncClient")

    tool = RedditSearchTool(user_agent="argus-test/0.1")
    hits = await tool.search("")

    assert hits == []
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_search_dedupes_urls(mocker) -> None:
    payload = _listing(
        [
            {"url": "https://example.com/a", "title": "A", "selftext": ""},
            {"url": "https://example.com/a", "title": "A dup", "selftext": ""},
        ]
    )
    _patch_client(mocker, _resp(payload))

    tool = RedditSearchTool(user_agent="argus-test/0.1")
    hits = await tool.search("query")

    assert len(hits) == 1
