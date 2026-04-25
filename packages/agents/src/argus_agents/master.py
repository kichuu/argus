from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, AgentRole, EvidenceRef, Persona
from argus_core.settings import get_settings
from argus_extraction.providers import Provider
from pydantic import BaseModel, Field, ValidationError

from argus_agents.base import Agent
from argus_agents.state import DiscussionState

logger = get_logger(__name__)


class _PersonaProposal(BaseModel):
    frame: str
    description: str
    knowledge_emphasis: list[str] = Field(default_factory=list)


class _PersonaSlate(BaseModel):
    personas: list[_PersonaProposal] = Field(min_length=3, max_length=5)


_STOCK_PERSONAS: list[dict[str, object]] = [
    {
        "frame": "skeptical empiricist",
        "description": (
            "Foregrounds measurement, replication, and prior probability. Pushes back on"
            " under-evidenced claims and asks what would change their mind."
        ),
        "knowledge_emphasis": ["statistics", "study design", "base rates"],
    },
    {
        "frame": "regulator viewpoint",
        "description": (
            "Reads the evidence through the lens of accountability, compliance, and"
            " stakeholder protection. Cares about jurisdiction, precedent, and enforcement."
        ),
        "knowledge_emphasis": ["policy", "compliance", "jurisdiction"],
    },
    {
        "frame": "operator on the ground",
        "description": (
            "Speaks for the practitioner who has to act on the claims today. Cares about"
            " feasibility, second-order effects, and what the evidence omits."
        ),
        "knowledge_emphasis": ["operations", "feasibility", "tradeoffs"],
    },
    {
        "frame": "historical analogue analyst",
        "description": (
            "Looks for precedent and pattern. Asks what comparable past episodes predict"
            " and where the analogy breaks down."
        ),
        "knowledge_emphasis": ["history", "case studies", "pattern matching"],
    },
    {
        "frame": "affected-stakeholder advocate",
        "description": (
            "Centers the people most exposed to outcomes implied by the evidence. Cares"
            " about distributional impact and voices missing from the pack."
        ),
        "knowledge_emphasis": ["equity", "stakeholder impact", "distributional effects"],
    },
]


_MASTER_PROMPT = """You design a panel of 3-5 epistemic frames to discuss the topic.
A frame is a viewpoint label (e.g. "regulator viewpoint", "skeptical scientist"),
NEVER a named living person and NEVER instructions to impersonate.

Topic: {topic}

Evidence pack (verbatim spans):
{evidence_block}

Stock frames you may select from (you may also propose new ones in the same style):
{stock_block}

Return JSON matching the schema. Each frame: short label, one-paragraph description,
and 2-5 knowledge_emphasis tags. Do not write phrases like "you are X" or "act as X"."""


class MasterAgent(Agent):
    def __init__(self, provider: Provider, model: str | None = None) -> None:
        super().__init__(AgentRole.MASTER, model or get_settings().default_master_model)
        self.provider = provider

    async def step(self, state: DiscussionState) -> DiscussionState:
        evidence_block = "\n".join(
            f"- [ev:{e.source_id}] {e.verbatim_span!r}"
            for e in state.evidence_pack.evidence[:32]
        ) or "(no evidence)"
        stock_block = "\n".join(
            f"- {p['frame']}: {p['description']}" for p in _STOCK_PERSONAS
        )
        prompt = _MASTER_PROMPT.format(
            topic=state.topic,
            evidence_block=evidence_block,
            stock_block=stock_block,
        )

        slate: _PersonaSlate | None = None
        try:
            result = await self.provider.structured_extract(prompt, _PersonaSlate, self.model)
            if isinstance(result, _PersonaSlate):
                slate = result
            else:
                state.errors.append("master: provider returned wrong type")
        except Exception as e:
            logger.error("master_llm_failed", error=str(e))
            state.errors.append(f"master: {e}")

        personas: list[Persona] = []
        if slate is not None:
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

        # Phase 4 baseline: if the LLM produced nothing usable, fall back to the
        # hardcoded stock so the rest of the graph can still execute.
        if not personas:
            logger.warning("master_falling_back_to_stock_personas")
            for prop in _STOCK_PERSONAS[:3]:
                try:
                    personas.append(
                        Persona(
                            frame=str(prop["frame"]),
                            description=str(prop["description"]),
                            knowledge_emphasis=list(prop["knowledge_emphasis"]),  # type: ignore[arg-type]
                        )
                    )
                except ValidationError:
                    continue

        state.personas = personas

        cited_refs: list[EvidenceRef] = list(state.evidence_pack.evidence[:5])
        cast_summary = "; ".join(p.frame for p in personas) or "(no personas)"
        state.messages.append(
            AgentMessage(
                discussion_id=state.discussion_id,
                agent_id="master",
                role=AgentRole.MASTER,
                content=f"Cast {len(personas)} persona frame(s) for the discussion: {cast_summary}.",
                evidence_refs=cited_refs,
            )
        )
        logger.info("master_personas_built", count=len(personas))
        return state
