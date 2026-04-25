from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from argus_core.schemas.evidence import EvidenceRef


class ClaimStatus(StrEnum):
    LIKELY_TRUE = "likely_true"
    CONTESTED = "contested"
    UNVERIFIED = "unverified"
    LIKELY_FALSE = "likely_false"


class AgentConsensus(BaseModel):
    agree: int = Field(ge=0, default=0)
    disagree: int = Field(ge=0, default=0)
    uncertain: int = Field(ge=0, default=0)


class Claim(BaseModel):
    """An atomic statement about the world, backed by evidence.

    Hard rule: every Claim must have at least one supporting EvidenceRef.
    Construction without evidence raises ValidationError.
    """

    id: UUID = Field(default_factory=uuid4)
    statement: str = Field(min_length=1)
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[EvidenceRef] = Field(min_length=1)
    contradicting_evidence: list[EvidenceRef] = Field(default_factory=list)
    affected_entities: list[UUID] = Field(default_factory=list)
    agent_consensus: AgentConsensus = Field(default_factory=AgentConsensus)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def must_have_supporting_evidence(self) -> Self:
        if not self.supporting_evidence:
            raise ValueError("a claim must have at least one supporting EvidenceRef")
        return self
