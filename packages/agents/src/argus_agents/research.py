from typing import Any

from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, AgentRole, EvidenceRef
from argus_core.settings import get_settings

from argus_agents.base import Agent
from argus_agents.state import DiscussionState, EvidencePack

logger = get_logger(__name__)


class ResearchAgent(Agent):
    """Builds the evidence pack for the discussion.

    The research step is retrieval-only (no LLM call): the retriever IS the
    "model" here. It populates `state.evidence_pack.evidence` from the spans
    returned by `retriever.retrieve(topic, top_k=...)`, then writes a single
    AgentMessage summarising what it found so downstream agents (and the UI)
    have a record of how the pack was assembled.
    """

    def __init__(self, retriever: Any, model: str | None = None, top_k: int = 20) -> None:
        super().__init__(AgentRole.RESEARCH, model or get_settings().default_research_model)
        self.retriever = retriever
        self.top_k = top_k

    async def step(self, state: DiscussionState) -> DiscussionState:
        spans = await self.retriever.retrieve(state.topic, top_k=self.top_k)

        evidence: list[EvidenceRef] = []
        entity_ids: set = set()
        for span in spans:
            try:
                ref = EvidenceRef(
                    source_id=span.source_id,
                    verbatim_span=span.verbatim_span,
                    char_start=span.char_start,
                    char_end=span.char_end,
                    fetched_at=span.fetched_at,
                    trust_tier=span.trust_tier,
                )
            except Exception as e:
                logger.warning("research_span_rejected", error=str(e))
                state.errors.append(f"research: {e}")
                continue
            evidence.append(ref)
            for eid in getattr(span, "entity_ids", []) or []:
                entity_ids.add(eid)

        state.evidence_pack = EvidencePack(
            topic=state.topic,
            evidence=evidence,
            entities=sorted(entity_ids, key=str),
        )

        summary_lines = [
            f"Research pulled {len(evidence)} evidence span(s) for topic {state.topic!r}."
        ]
        for ev in evidence[:8]:
            snippet = ev.verbatim_span[:120].replace("\n", " ")
            summary_lines.append(f"- [ev:{ev.source_id}] {snippet}")
        content = "\n".join(summary_lines)

        state.messages.append(
            AgentMessage(
                discussion_id=state.discussion_id,
                agent_id="research",
                role=AgentRole.RESEARCH,
                content=content,
                evidence_refs=list(evidence),
            )
        )

        logger.info(
            "research_pack_built",
            topic=state.topic,
            evidence_count=len(evidence),
            entity_count=len(entity_ids),
        )
        return state
