from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, AgentRole, EvidenceRef, Persona
from argus_core.settings import get_settings
from argus_extraction.providers import Provider

from argus_agents.base import _EV_PATTERN, Agent, strip_unsupported_claims
from argus_agents.state import DiscussionState

logger = get_logger(__name__)

_PERSONA_PROMPT = """You speak from the frame: {frame}.

Frame description: {description}
Knowledge emphasis: {emphasis}

Topic: {topic}

You may ONLY assert things that are directly supported by the evidence pack below.
After every assertion, cite the supporting evidence inline as [ev:<UUID>].
If no evidence in the pack supports a point, do not state it.
Do not invent UUIDs. Do not impersonate a real named person.

Evidence pack:
{evidence_block}

Write 3-6 short, declarative sentences. Each must end with at least one [ev:...] citation."""


class PersonaAgent(Agent):
    def __init__(self, persona: Persona, provider: Provider, model: str | None = None) -> None:
        super().__init__(AgentRole.PERSONA, model or get_settings().default_persona_model)
        self.persona = persona
        self.provider = provider

    async def step(self, state: DiscussionState) -> DiscussionState:
        pack = state.evidence_pack
        evidence_block = "\n".join(
            f"- [ev:{e.source_id}] {e.verbatim_span!r}" for e in pack.evidence
        ) or "(no evidence)"

        prompt = _PERSONA_PROMPT.format(
            frame=self.persona.frame,
            description=self.persona.description,
            emphasis=", ".join(self.persona.knowledge_emphasis) or "(none)",
            topic=state.topic,
            evidence_block=evidence_block,
        )

        try:
            raw = await self.provider.text_complete(prompt, self.model, max_tokens=800)
        except Exception as e:
            logger.error("persona_llm_failed", frame=self.persona.frame, error=str(e))
            state.errors.append(f"persona[{self.persona.frame}]: {e}")
            return state

        allowed_ids = {e.source_id for e in pack.evidence}
        cleaned, stripped = strip_unsupported_claims(raw, allowed_ids)

        if stripped:
            logger.info(
                "persona_stripped_unsupported",
                frame=self.persona.frame,
                count=len(stripped),
            )

        if not cleaned.strip():
            state.errors.append(
                f"persona[{self.persona.frame}]: no supported assertions remained"
            )
            return state

        cited_ids = {sid.lower() for sid in _EV_PATTERN.findall(cleaned)}
        refs: list[EvidenceRef] = [
            e for e in pack.evidence if str(e.source_id).lower() in cited_ids
        ]

        msg = AgentMessage(
            discussion_id=state.discussion_id,
            agent_id=f"persona:{self.persona.id}",
            persona_id=self.persona.id,
            role=AgentRole.PERSONA,
            content=cleaned,
            evidence_refs=refs,
        )
        state.messages.append(msg)
        return state
