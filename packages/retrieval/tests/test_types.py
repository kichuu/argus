from datetime import UTC, datetime
from uuid import uuid4

import pytest
from argus_retrieval.types import RetrievedSpan
from pydantic import ValidationError


def test_retrieved_span_validates() -> None:
    span = RetrievedSpan(
        verbatim_span="hello world",
        char_start=0,
        char_end=11,
        source_id=uuid4(),
        fetched_at=datetime.now(UTC),
        trust_tier=2,
        score=0.91,
    )
    assert span.verbatim_span == "hello world"
    assert span.entity_ids == []


def test_retrieved_span_rejects_offset_mismatch() -> None:
    with pytest.raises(ValidationError):
        RetrievedSpan(
            verbatim_span="hello",
            char_start=0,
            char_end=11,
            source_id=uuid4(),
            fetched_at=datetime.now(UTC),
            trust_tier=2,
            score=0.5,
        )


def test_retrieved_span_rejects_inverted_offsets() -> None:
    with pytest.raises(ValidationError):
        RetrievedSpan(
            verbatim_span="hi",
            char_start=10,
            char_end=10,
            source_id=uuid4(),
            fetched_at=datetime.now(UTC),
            trust_tier=1,
            score=0.0,
        )


def test_retrieved_span_trust_tier_bounds() -> None:
    with pytest.raises(ValidationError):
        RetrievedSpan(
            verbatim_span="hi",
            char_start=0,
            char_end=2,
            source_id=uuid4(),
            fetched_at=datetime.now(UTC),
            trust_tier=5,
            score=0.0,
        )
