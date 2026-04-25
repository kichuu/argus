from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from argus_retrieval.types import RetrievedSpan
from argus_retrieval.vector import DENSE_VECTOR_NAME, VectorIndex


def _make_span() -> RetrievedSpan:
    return RetrievedSpan(
        verbatim_span="hello world",
        char_start=0,
        char_end=11,
        source_id=uuid4(),
        fetched_at=datetime.now(UTC),
        trust_tier=2,
        score=0.0,
        entity_ids=[uuid4()],
    )


@pytest.mark.asyncio
async def test_ensure_collection_skips_when_existing() -> None:
    fake_client = MagicMock()
    fake_client.collection_exists = AsyncMock(return_value=True)
    fake_client.create_collection = AsyncMock()

    vi = VectorIndex(client=fake_client, collection="argus_evidence")
    await vi.ensure_collection()

    fake_client.collection_exists.assert_awaited_once_with("argus_evidence")
    fake_client.create_collection.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_collection_creates_when_missing() -> None:
    fake_client = MagicMock()
    fake_client.collection_exists = AsyncMock(return_value=False)
    fake_client.create_collection = AsyncMock()

    vi = VectorIndex(client=fake_client, collection="argus_evidence")
    await vi.ensure_collection()

    fake_client.create_collection.assert_awaited_once()
    kwargs = fake_client.create_collection.await_args.kwargs
    assert kwargs["collection_name"] == "argus_evidence"
    assert DENSE_VECTOR_NAME in kwargs["vectors_config"]


@pytest.mark.asyncio
async def test_upsert_span_sends_payload_with_expected_keys() -> None:
    fake_client = MagicMock()
    fake_client.upsert = AsyncMock()

    vi = VectorIndex(client=fake_client, collection="argus_evidence")
    span = _make_span()
    await vi.upsert_span(
        span,
        dense_vec=[0.0] * 4,
        payload_extras={"claim_id": "cid-1"},
    )

    fake_client.upsert.assert_awaited_once()
    kwargs = fake_client.upsert.await_args.kwargs
    points = kwargs["points"]
    assert len(points) == 1
    payload = points[0].payload
    # The payload superset includes all of the keys we filter/return on:
    for key in (
        "verbatim_span",
        "char_start",
        "char_end",
        "source_id",
        "fetched_at",
        "trust_tier",
        "entity_ids",
        "claim_id",
    ):
        assert key in payload
    assert payload["claim_id"] == "cid-1"
    assert payload["source_id"] == str(span.source_id)
