from argus_core.db.models import PersonaModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, AgentRole, EvidenceRef, Persona
from argus_core.settings import get_settings
from argus_extraction.providers import Provider
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from argus_agents.base import Agent
from argus_agents.state import DiscussionState

logger = get_logger(__name__)


_FALLBACK_COLORS = [
    "var(--p-1)",
    "var(--p-2)",
    "var(--p-3)",
    "var(--p-4)",
    "var(--p-5)",
    "var(--p-6)",
    "var(--p-7)",
]


def color_for_frame(frame: str) -> str:
    """Derive a stable, frame-hash-based color for personas without an explicit color."""
    h = sum(ord(c) for c in frame) if frame else 0
    return _FALLBACK_COLORS[h % len(_FALLBACK_COLORS)]


class _PersonaSelection(BaseModel):
    chosen_persona_ids: list[str] = Field(min_length=3, max_length=5)


# Tiny embedded fallback used only when the personas table is empty so a
# fresh DB still produces a valid discussion. Mirrors the three core frames
# from earlier prototypes.
_FALLBACK_PERSONAS: list[dict[str, object]] = [
    {
        "frame": "skeptical empiricist",
        "description": (
            "Foregrounds measurement, replication, and prior probability. Pushes"
            " back on under-evidenced claims and asks what would change their mind."
        ),
        "knowledge_emphasis": ["statistics", "study design", "base rates"],
    },
    {
        "frame": "regulator viewpoint",
        "description": (
            "Reads the evidence through the lens of accountability, compliance,"
            " and stakeholder protection. Cares about jurisdiction, precedent,"
            " and enforcement."
        ),
        "knowledge_emphasis": ["policy", "compliance", "jurisdiction"],
    },
    {
        "frame": "operator on the ground",
        "description": (
            "Speaks for the practitioner who has to act on the claims today."
            " Cares about feasibility, second-order effects, and what the"
            " evidence omits."
        ),
        "knowledge_emphasis": ["operations", "feasibility", "tradeoffs"],
    },
]


_MASTER_PROMPT = """You are casting a panel of 3-5 epistemic frames to discuss the topic.
A frame is a viewpoint label (e.g. "regulator viewpoint", "skeptical scientist"),
NEVER a named living person and NEVER instructions to impersonate.

Topic: {topic}

Evidence pack (verbatim spans):
{evidence_block}

Available personas (pick 3-5 of these by id, choosing the frames best suited
to the topic and evidence; balance perspectives where possible):
{persona_block}

Return JSON matching the schema. `chosen_persona_ids` MUST contain between 3
and 5 ids drawn verbatim from the list above."""


def _row_to_persona(row: PersonaModel) -> Persona:
    """Translate a DB row into a Pydantic Persona, deriving color when null."""
    color = row.color or color_for_frame(row.frame)
    return Persona(
        id=row.id,
        frame=row.frame,
        description=row.description,
        knowledge_emphasis=list(row.knowledge_emphasis or []),
        temperature=row.temperature if row.temperature is not None else 0.7,
        redlines=list(row.redlines or []),
        bias=row.bias,
        model_assignment=row.model_assignment,
        color=color,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class MasterAgent(Agent):
    def __init__(self, provider: Provider, model: str | None = None) -> None:
        super().__init__(AgentRole.MASTER, model or get_settings().default_master_model)
        self.provider = provider

    async def step(self, state: DiscussionState) -> DiscussionState:
        # 1. Load up to 20 most-recent personas from the DB.
        db_rows: list[PersonaModel] = []
        try:
            async with session_scope() as session:
                stmt = (
                    select(PersonaModel)
                    .order_by(PersonaModel.created_at.desc())
                    .limit(20)
                )
                result = await session.execute(stmt)
                db_rows = list(result.scalars().all())
        except Exception as e:
            logger.error("master_db_load_failed", error=str(e))
            state.errors.append(f"master: db load failed: {e}")

        personas: list[Persona] = []

        if not db_rows:
            # 2. Fallback: tiny embedded list, sufficient to keep the graph alive.
            logger.warning("master.no_personas_in_db_using_fallback")
            for prop in _FALLBACK_PERSONAS:
                try:
                    frame = str(prop["frame"])
                    personas.append(
                        Persona(
                            frame=frame,
                            description=str(prop["description"]),
                            knowledge_emphasis=list(prop["knowledge_emphasis"]),  # type: ignore[arg-type]
                            color=color_for_frame(frame),
                        )
                    )
                except ValidationError as ve:
                    logger.warning(
                        "master_fallback_persona_rejected",
                        frame=prop.get("frame"),
                        error=str(ve),
                    )
                    continue
        else:
            # 3. Ask the master model to pick 3-5 personas from the DB list.
            row_by_id = {str(r.id): r for r in db_rows}
            persona_block = "\n".join(
                f"- id={r.id} | {r.frame}: {r.description}" for r in db_rows
            )
            evidence_block = "\n".join(
                f"- [ev:{e.source_id}] {e.verbatim_span!r}"
                for e in state.evidence_pack.evidence[:32]
            ) or "(no evidence)"
            prompt = _MASTER_PROMPT.format(
                topic=state.topic,
                evidence_block=evidence_block,
                persona_block=persona_block,
            )

            selection: _PersonaSelection | None = None
            try:
                result = await self.provider.structured_extract(
                    prompt, _PersonaSelection, self.model
                )
                if isinstance(result, _PersonaSelection):
                    selection = result
                else:
                    state.errors.append("master: provider returned wrong type")
            except Exception as e:
                logger.error("master_llm_failed", error=str(e))
                state.errors.append(f"master: {e}")

            chosen_rows: list[PersonaModel] = []
            if selection is not None:
                for pid in selection.chosen_persona_ids:
                    row = row_by_id.get(pid)
                    if row is not None and row not in chosen_rows:
                        chosen_rows.append(row)

            # 7. If the LLM returned nothing usable, fall back to the most-recent
            #    DB rows so the discussion still proceeds.
            if not chosen_rows:
                logger.warning("master_falling_back_to_recent_db_personas")
                chosen_rows = db_rows[: min(5, max(3, len(db_rows)))]

            for row in chosen_rows[:5]:
                try:
                    personas.append(_row_to_persona(row))
                except ValidationError as ve:
                    logger.warning("master_persona_rejected", frame=row.frame, error=str(ve))
                    state.errors.append(f"master: rejected persona {row.frame!r}: {ve}")
                    continue

        # 5. Write to state.
        state.personas = personas

        # 6. Append the master message describing the cast.
        cited_refs: list[EvidenceRef] = list(state.evidence_pack.evidence[:5])
        cast_summary = ", ".join(p.frame for p in personas) or "(no personas)"
        state.messages.append(
            AgentMessage(
                discussion_id=state.discussion_id,
                agent_id="master",
                role=AgentRole.MASTER,
                content=f"Cast {len(personas)} persona(s): {cast_summary}",
                evidence_refs=cited_refs,
            )
        )
        logger.info("master_personas_built", count=len(personas))
        return state
