from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from argus_retrieval.hybrid import HybridRetriever
from argus_retrieval.types import RetrievedSpan


def _make_span(score: float = 0.5) -> RetrievedSpan:
    return RetrievedSpan(
        verbatim_span="The quick brown fox",
        char_start=0,
        char_end=19,
        source_id=uuid4(),
        fetched_at=datetime.now(timezone.utc),
        trust_tier=2,
        score=score,
        entity_ids=[],
    )


@pytest.mark.asyncio
async def test_retrieval_chain_orders_calls(mocker) -> None:
    candidate = _make_span(score=0.42)
    reranked = _make_span(score=0.99)

    embedder = MagicMock()
    embedder.embed_one = AsyncMock(return_value=[0.0] * 4)

    vector = MagicMock()
    vector.search_dense = AsyncMock(return_value=[candidate])

    graph = MagicMock()
    neighbor_id = uuid4()
    graph.neighbors = AsyncMock(return_value=[neighbor_id])

    reranker = MagicMock()
    reranker.rerank = AsyncMock(return_value=[reranked])

    retriever = HybridRetriever(vector, graph, reranker, embedder)

    mention = uuid4()
    out = await retriever.retrieve(
        "what happened today?", mentioned_entities=[mention], top_k=5
    )

    assert out == [reranked]
    embedder.embed_one.assert_awaited_once_with("what happened today?")
    graph.neighbors.assert_awaited()
    vector.search_dense.assert_awaited_once()
    reranker.rerank.assert_awaited_once()
    args, kwargs = vector.search_dense.call_args
    entity_filter = kwargs.get("entity_filter")
    assert entity_filter is not None
    assert mention in entity_filter
    assert neighbor_id in entity_filter


@pytest.mark.asyncio
async def test_retrieval_without_entities_skips_graph(mocker) -> None:
    candidate = _make_span()
    embedder = MagicMock()
    embedder.embed_one = AsyncMock(return_value=[0.1] * 4)

    vector = MagicMock()
    vector.search_dense = AsyncMock(return_value=[candidate])

    graph = MagicMock()
    graph.neighbors = AsyncMock()

    reranker = MagicMock()
    reranker.rerank = AsyncMock(return_value=[candidate])

    retriever = HybridRetriever(vector, graph, reranker, embedder)
    out = await retriever.retrieve("query", top_k=3, recency_boost=False)

    assert out == [candidate]
    graph.neighbors.assert_not_awaited()
    args, kwargs = vector.search_dense.call_args
    assert kwargs.get("entity_filter") is None
