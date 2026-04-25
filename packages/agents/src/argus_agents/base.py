import re
from abc import ABC, abstractmethod
from uuid import UUID

from argus_core.logging import get_logger
from argus_core.schemas import AgentRole

from argus_agents.state import DiscussionState

logger = get_logger(__name__)

_EV_PATTERN = re.compile(r"\[ev:([0-9a-fA-F-]{36})\]")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class Agent(ABC):
    role: AgentRole
    model: str

    def __init__(self, role: AgentRole, model: str) -> None:
        self.role = role
        self.model = model

    @property
    def provider_name(self) -> str:
        from argus_extraction.providers import family_of

        return family_of(self.model)

    @abstractmethod
    async def step(self, state: DiscussionState) -> DiscussionState: ...


def strip_unsupported_claims(
    content: str,
    allowed_evidence_ids: set[UUID],
) -> tuple[str, list[str]]:
    sentences = _SENTENCE_SPLIT.split(content.strip())
    kept: list[str] = []
    stripped: list[str] = []
    allowed_str = {str(eid) for eid in allowed_evidence_ids}

    for raw in sentences:
        sentence = raw.strip()
        if not sentence:
            continue
        ids = _EV_PATTERN.findall(sentence)
        if not ids:
            stripped.append(sentence)
            continue
        if any(found.lower() not in allowed_str for found in ids):
            stripped.append(sentence)
            continue
        kept.append(sentence)

    return " ".join(kept), stripped
