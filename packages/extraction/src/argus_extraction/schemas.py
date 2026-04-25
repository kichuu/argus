from argus_core.schemas import EntityType, RelationType
from pydantic import BaseModel, Field


class ExtractedClaim(BaseModel):
    statement: str = Field(min_length=1)
    verbatim_span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    entities_mentioned: list[str] = Field(default_factory=list)


class ExtractedEntity(BaseModel):
    name: str = Field(min_length=1)
    entity_type: EntityType
    verbatim_span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class ExtractedRelation(BaseModel):
    subject: str = Field(min_length=1)
    relation_type: RelationType
    object: str = Field(min_length=1)
    verbatim_span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class ExtractionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
