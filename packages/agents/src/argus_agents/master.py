from argus_core.logging import get_logger
from argus_core.personas import PersonaLibrary, load_persona_library
from argus_core.schemas import AgentRole, Persona
from argus_core.settings import get_settings
from argus_extraction.providers import Provider
from pydantic import BaseModel, Field, ValidationError

from argus_agents.base import Agent
from argus_agents.state import DiscussionState

logger = get_logger(__name__)

_DEFAULT_LIBRARY_PERSONA_COUNT = 4


class _PersonaProposal(BaseModel):
    frame: str
    description: str
    knowledge_emphasis: list[str] = Field(default_factory=list)


class _PersonaSlate(BaseModel):
    personas: list[_PersonaProposal] = Field(min_length=3, max_length=5)


_MASTER_PROMPT = """You design a panel of 3-5 epistemic frames to discuss the topic.
A frame is a viewpoint label (e.g. "regulator viewpoint", "skeptical scientist"),
NEVER a named living person and NEVER instructions to impersonate.

Topic: {topic}

Evidence pack (verbatim spans):
{evidence_block}

Return JSON matching the schema. Each frame: short label, one-paragraph description,
and 2-5 knowledge_emphasis tags. Do not write phrases like "you are X" or "act as X"."""


class MasterAgent(Agent):
    def __init__(
        self,
        provider: Provider,
        model: str | None = None,
        *,
        library: PersonaLibrary | None = None,
        library_persona_count: int = _DEFAULT_LIBRARY_PERSONA_COUNT,
    ) -> None:
        super().__init__(AgentRole.MASTER, model or get_settings().default_master_model)
        self.provider = provider
        self.library = library if library is not None else load_persona_library()
        self.library_persona_count = library_persona_count

    async def step(self, state: DiscussionState) -> DiscussionState:
        vertical = state.evidence_pack.vertical
        if vertical and self._library_has_vertical(vertical):
            personas = self._personas_from_library(vertical)
            if personas:
                state.personas = personas
                logger.info(
                    "master_personas_from_library",
                    count=len(personas),
                    vertical=vertical,
                )
                return state

        return await self._invent_personas(state)

    def _library_has_vertical(self, vertical: str) -> bool:
        return bool(self.library.verticals.get(vertical))

    def _personas_from_library(self, vertical: str) -> list[Persona]:
        templates = self.library.for_vertical(vertical, include_general=False)
        chosen = templates[: self.library_persona_count]
        return self.library.to_personas(chosen)

    async def _invent_personas(self, state: DiscussionState) -> DiscussionState:
        evidence_block = "\n".join(
            f"- [ev:{e.source_id}] {e.verbatim_span!r}"
            for e in state.evidence_pack.evidence[:32]
        ) or "(no evidence)"
        prompt = _MASTER_PROMPT.format(topic=state.topic, evidence_block=evidence_block)

        try:
            slate = await self.provider.structured_extract(prompt, _PersonaSlate, self.model)
        except Exception as e:
            logger.error("master_llm_failed", error=str(e))
            state.errors.append(f"master: {e}")
            return state

        if not isinstance(slate, _PersonaSlate):
            state.errors.append("master: provider returned wrong type")
            return state

        personas: list[Persona] = []
        for prop in slate.personas:
            try:
                personas.append(
                    Persona(
                        frame=prop.frame,
                        description=prop.description,
                        knowledge_emphasis=prop.knowledge_emphasis,
                    )
                )
            except ValidationError as ve:
                logger.warning("master_persona_rejected", frame=prop.frame, error=str(ve))
                state.errors.append(f"master: rejected persona {prop.frame!r}: {ve}")
                continue

        state.personas = personas
        logger.info("master_personas_built", count=len(personas))
        return state
