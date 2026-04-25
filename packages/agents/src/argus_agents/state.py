from uuid import UUID, uuid4

from argus_core.schemas import AgentMessage, Claim, EvidenceRef, Persona
from pydantic import BaseModel, Field


class EvidencePack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    topic: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    entities: list[UUID] = Field(default_factory=list)


class DiscussionState(BaseModel):
    discussion_id: UUID
    topic: str
    evidence_pack: EvidencePack
    personas: list[Persona] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    final_claims: list[Claim] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
