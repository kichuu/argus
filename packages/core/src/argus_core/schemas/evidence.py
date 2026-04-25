from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class EvidenceRef(BaseModel):
    """A pointer to a verbatim span in a Source. The atomic unit of citation.

    Programmatic verifiers check that `verbatim_span == source.raw_text[char_start:char_end]`.
    Any agent assertion without a valid EvidenceRef must be rejected.
    """

    source_id: UUID
    verbatim_span: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    fetched_at: datetime
    trust_tier: int = Field(ge=1, le=4)

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        if self.char_start >= self.char_end:
            raise ValueError("char_start must be strictly less than char_end")
        if self.char_end - self.char_start != len(self.verbatim_span):
            raise ValueError(
                f"span length ({len(self.verbatim_span)}) does not match "
                f"char offset range ({self.char_end - self.char_start})"
            )
        return self
