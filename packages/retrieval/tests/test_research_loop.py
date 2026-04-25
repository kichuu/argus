from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from argus_retrieval.research_loop import ResearchLoop
from argus_retrieval.types import RetrievedSpan
from argus_retrieval.web_search import WebSearchHit


def _hn_tool(hits: list[WebSearchHit]) -> MagicMock:
    t = MagicMock()
    t.search = AsyncMock(return_value=hits)
    return t


def _reddit_tool(hits: list[WebSearchHit]) -> MagicMock:
    t = MagicMock()
    t.search = AsyncMock(return_value=hits)
    return t


def _make_span(score: float = 0.5) -> RetrievedSpan:
    return RetrievedSpan(
        verbatim_span="hello world",
        char_start=0,
        char_end=11,
        source_id=uuid4(),
        fetched_at=datetime.now(UTC),
        trust_tier=2,
        score=score,
        entity_ids=[],
    )


def _local_retriever(spans_per_call: list[list[RetrievedSpan]]) -> MagicMock:
    rt = MagicMock()
    rt.retrieve = AsyncMock(side_effect=spans_per_call)
    return rt


def _embedder(vec: list[float] | None = None) -> MagicMock:
    embed = MagicMock()
    embed.embed_one = AsyncMock(return_value=vec or [0.1] * 8)
    return embed


def _vector_index() -> MagicMock:
    vec = MagicMock()
    vec.upsert_span = AsyncMock(return_value=None)
    return vec


def _web_search(hits: list[WebSearchHit]) -> MagicMock:
    ws = MagicMock()
    ws.search = AsyncMock(return_value=hits)
    return ws


@pytest.mark.asyncio
async def test_retrieve_returns_local_when_min_hits_met() -> None:
    spans = [_make_span() for _ in range(5)]
    local = _local_retriever([spans])
    web = _web_search([WebSearchHit(url="https://x.com/")])

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=web,
        min_local_hits=5,
        mode="fallback",
    )

    out = await loop.retrieve("topic", top_k=10)

    assert out == spans
    local.retrieve.assert_awaited_once()
    web.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_retrieve_falls_back_to_web_when_below_min(mocker) -> None:
    cold = [_make_span()]
    warm = [_make_span() for _ in range(7)]
    local = _local_retriever([cold, warm])
    web = _web_search(
        [
            WebSearchHit(url="https://reuters.com/x", title="X", snippet="snip"),
            WebSearchHit(url="https://reuters.com/y", title="Y", snippet="snip"),
        ]
    )

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=web,
        min_local_hits=5,
        mode="fallback",
    )
    ingest = mocker.patch.object(
        loop, "_ingest_url", new=AsyncMock(return_value=MagicMock())
    )

    out = await loop.retrieve("novel topic", top_k=10)

    assert out == warm
    assert local.retrieve.await_count == 2
    web.search.assert_awaited_once()
    assert ingest.await_count == 2


@pytest.mark.asyncio
async def test_retrieve_skips_web_when_no_search_tool() -> None:
    cold = [_make_span()]
    local = _local_retriever([cold])

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=None,
        min_local_hits=5,
        mode="fallback",
    )

    out = await loop.retrieve("topic")

    assert out == cold
    local.retrieve.assert_awaited_once()


@pytest.mark.asyncio
async def test_augment_calls_all_three_sources_even_when_local_full(mocker) -> None:
    spans = [_make_span() for _ in range(10)]
    warm = [_make_span() for _ in range(12)]
    local = _local_retriever([spans, warm])
    web = _web_search(
        [WebSearchHit(url="https://reuters.com/a", title="A", snippet="")]
    )
    hn = _hn_tool(
        [WebSearchHit(url="https://news.ycombinator.com/x", title="HN X", snippet="")]
    )
    reddit = _reddit_tool(
        [WebSearchHit(url="https://example.com/r", title="R", snippet="")]
    )

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=web,
        hn_search=hn,
        reddit_search=reddit,
        min_local_hits=5,
        mode="augment",
    )
    ingest = mocker.patch.object(
        loop, "_ingest_url", new=AsyncMock(return_value=MagicMock())
    )

    out = await loop.retrieve("topic", top_k=10)

    assert out == warm
    web.search.assert_awaited_once()
    hn.search.assert_awaited_once()
    reddit.search.assert_awaited_once()
    assert ingest.await_count == 3
    assert local.retrieve.await_count == 2


@pytest.mark.asyncio
async def test_augment_dedupes_urls_across_sources(mocker) -> None:
    spans = [_make_span() for _ in range(3)]
    warm = [_make_span() for _ in range(4)]
    local = _local_retriever([spans, warm])
    shared = "https://shared.example.com/post"
    web = _web_search([WebSearchHit(url=shared, title="OAI", snippet="")])
    hn = _hn_tool([WebSearchHit(url=shared, title="HN", snippet="")])
    reddit = _reddit_tool(
        [WebSearchHit(url="https://other.example.com/x", title="R", snippet="")]
    )

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=web,
        hn_search=hn,
        reddit_search=reddit,
        mode="augment",
    )
    ingest = mocker.patch.object(
        loop, "_ingest_url", new=AsyncMock(return_value=MagicMock())
    )

    await loop.retrieve("topic", top_k=10)

    # shared URL ingested only once, plus the unique reddit URL
    assert ingest.await_count == 2
    ingested_urls = {call.args[0] for call in ingest.call_args_list}
    assert ingested_urls == {shared, "https://other.example.com/x"}


@pytest.mark.asyncio
async def test_augment_tolerates_none_tools(mocker) -> None:
    spans = [_make_span() for _ in range(3)]
    warm = [_make_span() for _ in range(4)]
    local = _local_retriever([spans, warm])
    hn = _hn_tool([WebSearchHit(url="https://example.com/h", title="H", snippet="")])

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=None,
        hn_search=hn,
        reddit_search=None,
        mode="augment",
    )
    ingest = mocker.patch.object(
        loop, "_ingest_url", new=AsyncMock(return_value=MagicMock())
    )

    await loop.retrieve("topic", top_k=10)

    hn.search.assert_awaited_once()
    assert ingest.await_count == 1


@pytest.mark.asyncio
async def test_augment_skips_requery_when_nothing_ingested(mocker) -> None:
    spans = [_make_span() for _ in range(3)]
    local = _local_retriever([spans])
    web = _web_search([])
    hn = _hn_tool([])
    reddit = _reddit_tool([])

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=web,
        hn_search=hn,
        reddit_search=reddit,
        mode="augment",
    )
    ingest = mocker.patch.object(
        loop, "_ingest_url", new=AsyncMock(return_value=None)
    )

    out = await loop.retrieve("topic", top_k=10)

    assert out == spans
    assert ingest.await_count == 0
    assert local.retrieve.await_count == 1


@pytest.mark.asyncio
async def test_augment_returns_local_when_no_sources_configured() -> None:
    spans = [_make_span() for _ in range(2)]
    local = _local_retriever([spans])

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=None,
        hn_search=None,
        reddit_search=None,
        mode="augment",
    )

    out = await loop.retrieve("topic")

    assert out == spans
    local.retrieve.assert_awaited_once()


@pytest.mark.asyncio
async def test_augment_tolerates_one_source_raising(mocker) -> None:
    spans = [_make_span() for _ in range(3)]
    warm = [_make_span() for _ in range(4)]
    local = _local_retriever([spans, warm])
    web = _web_search(
        [WebSearchHit(url="https://example.com/ok", title="OK", snippet="")]
    )
    hn = MagicMock()
    hn.search = AsyncMock(side_effect=RuntimeError("upstream down"))
    reddit = _reddit_tool(
        [WebSearchHit(url="https://example.com/r", title="R", snippet="")]
    )

    loop = ResearchLoop(
        local_retriever=local,
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=web,
        hn_search=hn,
        reddit_search=reddit,
        mode="augment",
    )
    ingest = mocker.patch.object(
        loop, "_ingest_url", new=AsyncMock(return_value=MagicMock())
    )

    out = await loop.retrieve("topic", top_k=10)

    assert out == warm
    # The two surviving sources contributed; HN raised and was skipped.
    assert ingest.await_count == 2


@pytest.mark.asyncio
async def test_ingest_url_skips_when_content_hash_already_indexed(mocker) -> None:
    fetched_html = "<html><head><title>T</title></head><body><p>Body text here.</p></body></html>"

    loop = ResearchLoop(
        local_retriever=MagicMock(),
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=None,
    )

    mocker.patch.object(loop, "_fetch", new=AsyncMock(return_value=fetched_html))

    # Simulate the DB returning an existing source row.
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=uuid4())
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(
        "argus_retrieval.research_loop.session_scope", MagicMock(return_value=cm)
    )

    out = await loop._ingest_url("https://example.com/a", hint_title="title")

    assert out is None
    session.add.assert_not_called()
    loop._vector.upsert_span.assert_not_called()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_ingest_url_persists_new_source_and_indexes(mocker) -> None:
    fetched_html = (
        "<html><head><title>News</title></head>"
        "<body><p>Important article body.</p></body></html>"
    )
    embedder = _embedder()
    vector = _vector_index()
    loop = ResearchLoop(
        local_retriever=MagicMock(),
        embedder=embedder,
        vector_index=vector,
        web_search=None,
    )

    mocker.patch.object(loop, "_fetch", new=AsyncMock(return_value=fetched_html))

    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=None)
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(
        "argus_retrieval.research_loop.session_scope", MagicMock(return_value=cm)
    )

    out = await loop._ingest_url("https://reuters.com/x", hint_title="hint")

    assert out is not None
    assert "Important article body" in out.raw_text
    session.add.assert_called_once()
    embedder.embed_one.assert_awaited_once()
    vector.upsert_span.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_url_returns_none_on_fetch_failure(mocker) -> None:
    loop = ResearchLoop(
        local_retriever=MagicMock(),
        embedder=_embedder(),
        vector_index=_vector_index(),
        web_search=None,
    )
    mocker.patch.object(loop, "_fetch", new=AsyncMock(return_value=None))

    out = await loop._ingest_url("https://broken.example.com/")

    assert out is None
