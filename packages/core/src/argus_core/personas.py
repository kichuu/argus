"""Persona library loader.

Loads a curated YAML library of persona frames per vertical so the MasterAgent
can seed reproducible debates instead of inventing frames each run. Frames are
validated at load time against the same impersonation patterns the runtime
``Persona`` model rejects, surfacing config errors immediately.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from argus_core.schemas import Persona
from argus_core.settings import get_settings

_BANNED_PATTERNS = (
    "you are ",
    "act as ",
    "pretend to be ",
)


class PersonaTemplate(BaseModel):
    """A persona definition stored in the library YAML.

    Mirrors the runtime ``Persona`` schema fields used at construction time,
    minus the auto-generated ``id`` / ``created_at``. The frame validator
    matches ``Persona``'s rules so bad config fails at load.
    """

    frame: str = Field(min_length=3, max_length=120)
    description: str
    knowledge_emphasis: list[str] = Field(default_factory=list)
    faction: str | None = None
    color_token: str | None = None

    @field_validator("frame")
    @classmethod
    def reject_impersonation(cls, v: str) -> str:
        lowered = v.lower()
        for bad in _BANNED_PATTERNS:
            if lowered.startswith(bad):
                raise ValueError(
                    f"persona frame must describe a viewpoint, not impersonate ({v!r})"
                )
        return v


class PersonaLibrary(BaseModel):
    """Curated persona templates indexed by vertical."""

    verticals: dict[str, list[PersonaTemplate]] = Field(default_factory=dict)

    def for_vertical(
        self,
        vertical: str,
        include_general: bool = True,
    ) -> list[PersonaTemplate]:
        """Return templates for ``vertical``, optionally appending ``general`` frames."""
        out: list[PersonaTemplate] = list(self.verticals.get(vertical, []))
        if include_general and vertical != "general":
            out.extend(self.verticals.get("general", []))
        return out

    def to_personas(self, templates: list[PersonaTemplate]) -> list[Persona]:
        """Materialize templates as runtime ``Persona`` instances."""
        return [
            Persona(
                frame=t.frame,
                description=t.description,
                knowledge_emphasis=list(t.knowledge_emphasis),
                faction=t.faction,
                color_token=t.color_token,
            )
            for t in templates
        ]


@lru_cache(maxsize=1)
def load_persona_library(path: Path | None = None) -> PersonaLibrary:
    """Load the YAML library; return an empty library if the file is missing."""
    settings = get_settings()
    target = path or settings.personas_path
    if not target.exists():
        return PersonaLibrary()
    raw = yaml.safe_load(target.read_text()) or {}
    if not isinstance(raw, dict) or "verticals" not in raw:
        return PersonaLibrary()
    return PersonaLibrary.model_validate(raw)
