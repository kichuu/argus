from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from argus_core.db.models import (
    AgentMessageModel,
    ClaimModel,
    DiscussionRunModel,
)
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import DiscussionStatus, EvidenceRef
from argus_core.settings import get_settings
from argus_extraction.providers import family_of, get_provider
from sqlalchemy import desc, select
from temporalio import activity

logger = get_logger(__name__)


@activity.defn
async def start_discussion(
    topic: str,
    vertical: str,
    discussion_id: str | None = None,
) -> str:
    did = UUID(discussion_id) if discussion_id else uuid4()
    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, did)
        if row is None:
            row = DiscussionRunModel(
                id=did,
                topic=topic,
                vertical=vertical,
                status=DiscussionStatus.PLANNING.value,
            )
            session.add(row)
        else:
            row.status = DiscussionStatus.PLANNING.value
    logger.info("start_discussion", discussion_id=str(did), topic=topic, vertical=vertical)
    return str(did)


async def _baseline_evidence_pack(vertical: str, limit: int = 20) -> list[dict[str, Any]]:
    """Phase 4 baseline: pull recent verified claims for the vertical.

    A real evidence pack uses HybridRetriever (vector + graph). That requires
    Qdrant + AGE up. For the baseline, scan the most recent claims with
    supporting evidence and let the discussion graph reason over them.
    """
    async with session_scope() as session:
        result = await session.execute(
            select(ClaimModel)
            .order_by(desc(ClaimModel.created_at))
            .limit(limit)
        )
        rows = result.scalars().all()
    pack: list[dict[str, Any]] = []
    for row in rows:
        for ev in row.supporting_evidence:
            try:
                ref = EvidenceRef.model_validate(ev)
            except Exception:  # noqa: BLE001
                continue
            pack.append(ref.model_dump(mode="json"))
    return pack


@activity.defn
async def assemble_evidence_pack(discussion_id: str) -> dict[str, Any]:
    did = UUID(discussion_id)
    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, did)
        if row is None:
            raise RuntimeError(f"discussion {discussion_id} not found")
        pack = await _baseline_evidence_pack(row.vertical)
        row.evidence_pack = pack
        row.status = DiscussionStatus.RESEARCHING.value
    logger.info(
        "assemble_evidence_pack.done",
        discussion_id=discussion_id,
        evidence_count=len(pack),
    )
    return {"discussion_id": discussion_id, "evidence_count": len(pack)}


class _EvidencePackRetriever:
    """Minimal retriever shim used by ResearchAgent during baseline.

    The real DiscussionGraph wants a HybridRetriever. For the Phase 4
    baseline we hand it a static evidence pack — ResearchAgent only calls
    `retrieve(query, ...)` and treats the result as the working set.
    """

    def __init__(self, evidence_dicts: list[dict[str, Any]]) -> None:
        self._evidence = [EvidenceRef.model_validate(e) for e in evidence_dicts]

    async def retrieve(self, query: str, **_: Any):  # noqa: D401, ARG002
        return list(self._evidence)


@activity.defn
async def run_discussion_graph(discussion_id: str) -> dict[str, Any]:
    from argus_agents.graph import DiscussionGraph  # local import — heavy

    did = UUID(discussion_id)
    settings = get_settings()

    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, did)
        if row is None:
            raise RuntimeError(f"discussion {discussion_id} not found")
        topic = row.topic
        evidence_dicts = list(row.evidence_pack or [])
        row.status = DiscussionStatus.DEBATING.value

    provider = get_provider("openai")
    retriever = _EvidencePackRetriever(evidence_dicts)

    graph = DiscussionGraph(
        retriever=retriever,
        master_provider=provider,
        persona_provider=provider,
        critic_provider=provider,
        synth_provider=provider,
        research_model=settings.default_research_model,
        master_model=settings.default_master_model,
        persona_model=settings.default_persona_model,
        critic_model=settings.default_critic_model,
        synth_model=settings.default_synthesis_model,
        extractor_family=family_of(settings.default_extractor_model),
    )

    state = await graph.run(topic, discussion_id=did)
    result = state.model_dump(mode="json")
    logger.info(
        "run_discussion_graph.done",
        discussion_id=discussion_id,
        messages=len(state.messages),
        final_claims=len(state.final_claims),
    )
    return result


@activity.defn
async def persist_results(discussion_id: str, graph_result: dict[str, Any]) -> dict[str, Any]:
    did = UUID(discussion_id)
    messages = graph_result.get("messages", []) or []
    final_claims = graph_result.get("final_claims", []) or []
    final_claim_ids = [str(c.get("id")) for c in final_claims if c.get("id")]

    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, did)
        if row is not None:
            row.final_claim_ids = final_claim_ids
            row.status = DiscussionStatus.COMPLETED.value
        for msg in messages:
            try:
                amid = UUID(str(msg.get("id"))) if msg.get("id") else uuid4()
            except (ValueError, TypeError):
                amid = uuid4()
            am = AgentMessageModel(
                id=amid,
                discussion_id=did,
                agent_id=str(msg.get("agent_id", "unknown")),
                persona_id=UUID(msg["persona_id"]) if msg.get("persona_id") else None,
                role=str(msg.get("role", "assistant")),
                content=str(msg.get("content", "")),
                evidence_refs=msg.get("evidence_refs", []) or [],
                parent_message_id=UUID(msg["parent_message_id"]) if msg.get("parent_message_id") else None,
            )
            session.add(am)

    logger.info(
        "persist_results.done",
        discussion_id=discussion_id,
        messages=len(messages),
        final_claims=len(final_claim_ids),
    )
    return {
        "discussion_id": discussion_id,
        "persisted": True,
        "messages": len(messages),
        "final_claims": len(final_claim_ids),
    }
