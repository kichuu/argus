from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from argus_retrieval.web_search import OpenAISearchTool, WebSearchHit


def _ns(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def _build_async_client_mock(mocker, response: object) -> MagicMock:
    client_instance = MagicMock()
    client_instance.responses = MagicMock()
    client_instance.responses.create = AsyncMock(return_value=response)
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=None)
    factory = mocker.patch("argus_retrieval.web_search.openai.AsyncOpenAI")
    factory.return_value = client_instance
    return client_instance


@pytest.mark.asyncio
async def test_search_parses_web_search_call_results(mocker) -> None:
    response = _ns(
        output=[
            _ns(
                type="web_search_call",
                results=[
                    _ns(
                        url="https://reuters.com/a",
                        title="Reuters A",
                        snippet="Snippet A",
                    ),
                    _ns(
                        url="https://apnews.com/b",
                        title="AP B",
                        snippet="Snippet B",
                    ),
                ],
            )
        ]
    )
    _build_async_client_mock(mocker, response)

    tool = OpenAISearchTool(model="gpt-test", api_key="dummy")
    hits = await tool.search("query", max_results=5)

    assert hits == [
        WebSearchHit(url="https://reuters.com/a", title="Reuters A", snippet="Snippet A"),
        WebSearchHit(url="https://apnews.com/b", title="AP B", snippet="Snippet B"),
    ]


@pytest.mark.asyncio
async def test_search_parses_message_url_citation_annotations(mocker) -> None:
    response = _ns(
        output=[
            _ns(
                type="message",
                content=[
                    _ns(
                        annotations=[
                            _ns(
                                type="url_citation",
                                url="https://wsj.com/c",
                                title="WSJ C",
                            )
                        ]
                    )
                ],
            )
        ]
    )
    _build_async_client_mock(mocker, response)

    tool = OpenAISearchTool(model="gpt-test", api_key="dummy")
    hits = await tool.search("query")

    assert hits == [WebSearchHit(url="https://wsj.com/c", title="WSJ C", snippet="")]


@pytest.mark.asyncio
async def test_search_dedupes_repeated_urls(mocker) -> None:
    response = _ns(
        output=[
            _ns(
                type="web_search_call",
                results=[
                    _ns(url="https://x.com/y", title="t1", snippet="s1"),
                    _ns(url="https://x.com/y", title="t2", snippet="s2"),
                ],
            )
        ]
    )
    _build_async_client_mock(mocker, response)

    tool = OpenAISearchTool(api_key="dummy")
    hits = await tool.search("query")

    assert len(hits) == 1
    assert hits[0].url == "https://x.com/y"


@pytest.mark.asyncio
async def test_search_returns_empty_when_shape_unrecognised(mocker) -> None:
    response = _ns(output=[_ns(type="something_else", payload={"foo": "bar"})])
    _build_async_client_mock(mocker, response)

    tool = OpenAISearchTool(api_key="dummy")
    hits = await tool.search("query")

    assert hits == []


@pytest.mark.asyncio
async def test_search_returns_empty_on_sdk_exception(mocker) -> None:
    client_instance = MagicMock()
    client_instance.responses = MagicMock()
    client_instance.responses.create = AsyncMock(side_effect=RuntimeError("boom"))
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=None)
    factory = mocker.patch("argus_retrieval.web_search.openai.AsyncOpenAI")
    factory.return_value = client_instance

    tool = OpenAISearchTool(api_key="dummy")
    hits = await tool.search("query")

    assert hits == []


@pytest.mark.asyncio
async def test_search_short_circuits_on_blank_query(mocker) -> None:
    factory = mocker.patch("argus_retrieval.web_search.openai.AsyncOpenAI")
    tool = OpenAISearchTool(api_key="dummy")

    hits = await tool.search("   ")

    assert hits == []
    factory.assert_not_called()


@pytest.mark.asyncio
async def test_search_respects_max_results(mocker) -> None:
    results = [
        _ns(url=f"https://example.com/{i}", title=f"t{i}", snippet="s") for i in range(10)
    ]
    response = _ns(output=[_ns(type="web_search_call", results=results)])
    _build_async_client_mock(mocker, response)

    tool = OpenAISearchTool(api_key="dummy")
    hits = await tool.search("query", max_results=3)

    assert len(hits) == 3
