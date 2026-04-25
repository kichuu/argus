from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RetrievedSpan(BaseModel):
    verbatim_span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    source_id: UUID
    fetched_at: datetime
    trust_tier: int = Field(ge=1, le=4)
    score: float
    entity_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_offsets(self) -> Self:
        if self.char_start >= self.char_end:
            raise ValueError("char_start must be strictly less than char_end")
        if self.char_end - self.char_start != len(self.verbatim_span):
            raise ValueError(
                f"span length ({len(self.verbatim_span)}) does not match "
                f"char offset range ({self.char_end - self.char_start})"
            )
        return self
