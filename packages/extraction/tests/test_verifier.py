import hashlib

import pytest
from argus_core.schemas import EvidenceRef, Source
from argus_extraction.verifier import (
    VerificationError,
    to_evidence_ref,
    verify_span,
)

RAW_TEXT = "The Fed raised rates by 25 basis points on March 1, 2025."


def _make_source() -> Source:
    return Source(
        title="test",
        content_hash=hashlib.sha256(RAW_TEXT.encode("utf-8")).hexdigest(),
        raw_text=RAW_TEXT,
        trust_tier=2,
    )


def test_verify_span_passes_for_exact_slice() -> None:
    source = _make_source()
    span = "25 basis points"
    start = RAW_TEXT.index(span)
    end = start + len(span)
    verify_span(source, span, start, end)


def test_verify_span_rejects_mismatched_offsets() -> None:
    source = _make_source()
    span = "25 basis points"
    start = RAW_TEXT.index(span)
    bad_end = start + len(span) - 1
    with pytest.raises(VerificationError):
        verify_span(source, span, start, bad_end)


def test_verify_span_rejects_mismatched_text() -> None:
    source = _make_source()
    span = "fifty basis points"
    start = RAW_TEXT.index("25 basis points")
    end = start + len("25 basis points")
    with pytest.raises(VerificationError):
        verify_span(source, span, start, end)


def test_verify_span_rejects_out_of_range() -> None:
    source = _make_source()
    with pytest.raises(VerificationError):
        verify_span(source, "anything", 0, len(RAW_TEXT) + 10)


def test_to_evidence_ref_returns_valid_ref() -> None:
    source = _make_source()
    span = "Fed"
    start = RAW_TEXT.index(span)
    end = start + len(span)
    ref = to_evidence_ref(source, span, start, end)
    assert isinstance(ref, EvidenceRef)
    assert ref.source_id == source.id
    assert ref.verbatim_span == span
    assert ref.char_start == start
    assert ref.char_end == end
    assert ref.trust_tier == source.trust_tier
    assert ref.fetched_at == source.fetched_at


def test_to_evidence_ref_raises_on_mismatch() -> None:
    source = _make_source()
    with pytest.raises(VerificationError):
        to_evidence_ref(source, "Fed", 0, 3)
