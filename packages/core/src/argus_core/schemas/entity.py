from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PERSON = "person"
    ORG = "org"
    PLACE = "place"
    EVENT = "event"
    POLICY = "policy"
    PRODUCT = "product"
    CONCEPT = "concept"


class Entity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    canonical_name: str
    entity_type: EntityType
    wikidata_id: str | None = Field(default=None, description="Wikidata Q-ID, e.g. Q42")
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
