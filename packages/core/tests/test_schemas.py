from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from argus_core.schemas import Claim, ClaimStatus, EvidenceRef, Persona


def _make_evidence(span: str = "the sky is blue", start: int = 0) -> EvidenceRef:
    return EvidenceRef(
        source_id=uuid4(),
        verbatim_span=span,
        char_start=start,
        char_end=start + len(span),
        fetched_at=datetime.now(timezone.utc),
        trust_tier=2,
    )


def test_evidence_offset_must_match_span_length():
    with pytest.raises(ValidationError):
        EvidenceRef(
            source_id=uuid4(),
            verbatim_span="hello",
            char_start=0,
            char_end=10,  # 10 - 0 != len("hello")
            fetched_at=datetime.now(timezone.utc),
            trust_tier=2,
        )


def test_claim_requires_supporting_evidence():
    with pytest.raises(ValidationError):
        Claim(
            statement="test",
            status=ClaimStatus.UNVERIFIED,
            confidence=0.5,
            supporting_evidence=[],
        )


def test_claim_with_evidence_is_valid():
    claim = Claim(
        statement="test",
        status=ClaimStatus.UNVERIFIED,
        confidence=0.5,
        supporting_evidence=[_make_evidence()],
    )
    assert claim.confidence == 0.5
    assert len(claim.supporting_evidence) == 1


def test_persona_rejects_impersonation_phrases():
    with pytest.raises(ValidationError):
        Persona(frame="Act as Janet Yellen", description="impersonating a person")
    with pytest.raises(ValidationError):
        Persona(frame="You are Elon Musk", description="impersonating a person")


def test_persona_accepts_frame():
    p = Persona(frame="regulator viewpoint", description="cautious oversight perspective")
    assert p.frame == "regulator viewpoint"
