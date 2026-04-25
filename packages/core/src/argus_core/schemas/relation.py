from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from argus_core.schemas.evidence import EvidenceRef


class RelationType(StrEnum):
    EMPLOYED_BY = "employed_by"
    LOCATED_IN = "located_in"
    PART_OF = "part_of"
    PARTICIPATED_IN = "participated_in"
    OWNS = "owns"
    AUTHORED = "authored"
    OPPOSES = "opposes"
    SUPPORTS = "supports"
    CAUSED = "caused"
    RELATED_TO = "related_to"


class Relation(BaseModel):
    """A directed edge between two entities, backed by evidence."""

    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    relation_type: RelationType
    object_id: UUID
    evidence: list[EvidenceRef] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
