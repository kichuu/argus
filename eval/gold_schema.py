from __future__ import annotations

from datetime import datetime
from typing import Literal

from argus_core.schemas import ClaimStatus
from pydantic import BaseModel, Field


class GoldEntity(BaseModel):
    name: str = Field(min_length=1)
    qid: str | None = None
    role: str | None = None


class GoldClaim(BaseModel):
    id: str
    source_url: str
    source_text: str
    statement: str
    expected_status: ClaimStatus
    expected_verbatim_span: str
    expected_char_start: int | None = None
    expected_char_end: int | None = None
    notes: str = ""

    vertical: str = "geopolitics"
    claim_type: Literal["factual", "quantitative", "attribution", "temporal"] | None = None
    entities: list[GoldEntity] = Field(default_factory=list)
    trust_tier: int | None = None
    publisher: str | None = None
    published_at: str | None = None
    labeler: str | None = None
    labeler_notes: str = ""
    verified: bool = False
    created_at: datetime | None = None
