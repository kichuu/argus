from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from argus_core.schemas.evidence import EvidenceRef


class DiscussionStatus(StrEnum):
    PLANNING = "planning"
    RESEARCHING = "researching"
    DEBATING = "debating"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRole(StrEnum):
    RESEARCH = "research"
    MASTER = "master"
    PERSONA = "persona"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"


class AgentMessage(BaseModel):
    """A single agent utterance.

    Every assertion in `content` must be backed by an entry in `evidence_refs`.
    Messages whose claims fail span verification are rejected upstream.
    """

    id: UUID = Field(default_factory=uuid4)
    discussion_id: UUID
    agent_id: str
    persona_id: UUID | None = None
    role: AgentRole
    content: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    parent_message_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiscussionRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    topic: str
    vertical: str
    status: DiscussionStatus = DiscussionStatus.PLANNING
    persona_ids: list[UUID] = Field(default_factory=list)
    evidence_pack: list[EvidenceRef] = Field(default_factory=list)
    final_claim_ids: list[UUID] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error: str | None = None
