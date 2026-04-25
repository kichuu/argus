from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

_BANNED_PATTERNS = (
    "you are ",
    "act as ",
    "pretend to be ",
)


class Persona(BaseModel):
    """A frame, not a person.

    Personas represent perspectives ("regulator viewpoint", "skeptical scientist"),
    never named living people. The `frame` field is validated to discourage
    impersonation patterns.
    """

    id: UUID = Field(default_factory=uuid4)
    frame: str = Field(min_length=3, max_length=120)
    description: str
    knowledge_emphasis: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def reject_impersonation(self) -> Self:
        lowered = self.frame.lower()
        for bad in _BANNED_PATTERNS:
            if lowered.startswith(bad):
                raise ValueError(
                    f"persona frame must describe a viewpoint, not impersonate ({self.frame!r})"
                )
        return self
