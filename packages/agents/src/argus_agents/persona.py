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

OUTPUT FORMAT — strict:
- Write 3-6 short declarative SENTENCES in plain English.
- Each sentence MUST contain real narrative text (subject + verb + object)
  — at least 6 words BEFORE any citation marker.
- After each sentence, append ONE OR TWO [ev:<UUID>] citations using ids
  from the evidence pack only. Never invent UUIDs.
- A sentence that contains ONLY citation markers (no narrative words) will
  be DISCARDED. Do not emit citation chains.
- Do not impersonate a real named person.
- Do not assert anything the evidence pack does not directly support.
  If your knowledge_emphasis isn't covered by the evidence, say so plainly
  in one sentence and cite the closest item.

Evidence pack:
{evidence_block}

Example of CORRECT shape:
  "The Federal Reserve held rates steady in the cited release [ev:abc...]. The minutes also flagged inflation persistence as a concern [ev:def...]."

Example of WRONG shape (will be discarded):
  "[ev:abc...] [ev:def...] [ev:ghi...]"

Now write your response from the frame above."""


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
