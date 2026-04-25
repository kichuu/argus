from typing import Any

from argus_core.logging import get_logger
from argus_core.schemas import AgentRole, EvidenceRef
from argus_core.settings import get_settings

from argus_agents.base import Agent
from argus_agents.state import DiscussionState, EvidencePack

logger = get_logger(__name__)


class ResearchAgent(Agent):
    def __init__(self, retriever: Any, model: str | None = None, top_k: int = 24) -> None:
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
        logger.info(
            "research_pack_built",
            topic=state.topic,
            evidence_count=len(evidence),
            entity_count=len(entity_ids),
        )
        return state
