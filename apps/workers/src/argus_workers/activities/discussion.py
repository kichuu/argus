from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from argus_core.db.models import (
    AgentMessageModel,
    ClaimModel,
    DiscussionRunModel,
)
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import DiscussionStatus
from argus_core.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio import activity

logger = get_logger(__name__)


async def _load_discussion(session: AsyncSession, discussion_id: str) -> DiscussionRunModel:
    row = await session.get(DiscussionRunModel, UUID(discussion_id))
    if row is None:
        raise LookupError(f"discussion {discussion_id} not found")
    return row


def _build_retriever() -> Any:
    """Construct a ResearchLoop wrapping HybridRetriever + OpenAI web_search.

    Local Qdrant is queried first; if hits < min_local_hits the loop falls
    back to OpenAI's hosted web_search, fetches each result via httpx,
    funnels through the ingestion pipeline (hash, dedup, persist Source,
    embed, upsert to Qdrant), then re-queries. Web hits inherit the same
    span-verification / trust-tier discipline as RSS sources.

    Imported lazily so unit tests can patch and so the activity import
    path doesn't pull heavy ML deps at module load.
    """
    from argus_retrieval import (
        Embedder,
        HybridRetriever,
        OpenAISearchTool,
        ResearchLoop,
        VectorIndex,
        get_reranker,
    )
    from argus_retrieval.graph import GraphQuerier

    embedder = Embedder()
    vector_index = VectorIndex()
    local = HybridRetriever(
        vector_index=vector_index,
        graph=GraphQuerier(),
        reranker=get_reranker(),
        embedder=embedder,
    )
    web_search = OpenAISearchTool() if get_settings().openai_api_key else None
    return ResearchLoop(
        local_retriever=local,
        embedder=embedder,
        vector_index=vector_index,
        web_search=web_search,
        min_local_hits=5,
    )


def _build_orchestrator(
    retriever: Any,
    *,
    on_post: Any = None,
    on_status: Any = None,
    on_phase: Any = None,
    on_claim: Any = None,
) -> Any:
    """Build a CouncilOrchestrator wired to the real OpenAIProvider."""
    from argus_agents import CouncilOrchestrator
    from argus_core.personas import load_persona_library
    from argus_extraction.providers import family_of, get_provider

    settings = get_settings()
    provider = get_provider("openai")
    return CouncilOrchestrator(
        provider=provider,
        retriever=retriever,
        library=load_persona_library(),
        on_post=on_post,
        on_status=on_status,
        on_phase=on_phase,
        on_claim=on_claim,
        master_model=settings.default_master_model,
        persona_model=settings.default_persona_model,
        critic_model=settings.default_critic_model,
        synthesis_model=settings.default_synthesis_model,
        research_model=settings.default_research_model,
        extractor_family=family_of(settings.default_extractor_model),
    )


@activity.defn
async def start_discussion(payload: dict[str, Any]) -> str:
    """Create the DiscussionRunModel row, return its id (UUID string)."""
    topic = str(payload["topic"])
    vertical = str(payload["vertical"])
    raw_id = payload.get("discussion_id")
    did = UUID(raw_id) if raw_id else uuid4()

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
            row.topic = topic
            row.vertical = vertical
            row.status = DiscussionStatus.PLANNING.value
            row.error = None
    logger.info(
        "start_discussion",
        discussion_id=str(did),
        topic=topic,
        vertical=vertical,
    )
    return str(did)


@activity.defn
async def assemble_evidence_pack(discussion_id: str) -> dict[str, Any]:
    """Run the research step: query the retriever, build EvidenceRef list,
    persist to discussion.evidence_pack JSONB. Return summary {n_evidence}."""
    from argus_core.schemas import EvidenceRef

    async with session_scope() as session:
        row = await _load_discussion(session, discussion_id)
        row.status = DiscussionStatus.RESEARCHING.value
        topic = row.topic

    retriever = _build_retriever()
    spans = await retriever.retrieve(topic, top_k=24)

    evidence: list[EvidenceRef] = []
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
        except Exception as exc:
            logger.warning("evidence_pack_span_rejected", error=str(exc))
            continue
        evidence.append(ref)

    serialized = [ref.model_dump(mode="json") for ref in evidence]

    async with session_scope() as session:
        row = await _load_discussion(session, discussion_id)
        row.evidence_pack = serialized

    logger.info(
        "assemble_evidence_pack",
        discussion_id=discussion_id,
        n_evidence=len(evidence),
    )
    return {"discussion_id": discussion_id, "n_evidence": len(evidence)}


@activity.defn
async def run_discussion_graph(discussion_id: str) -> dict[str, Any]:
    """Build OpenAIProvider + CouncilOrchestrator, run it, persist each
    AgentMessage as it's emitted, and broadcast events via Redis pub/sub
    so WS subscribers stream live. Returns {n_messages, n_claims}."""
    from argus_core.pubsub import DiscussionPubSub

    async with session_scope() as session:
        row = await _load_discussion(session, discussion_id)
        row.status = DiscussionStatus.DEBATING.value
        topic = row.topic
        vertical = row.vertical
        did = row.id

    retriever = _build_retriever()
    pubsub = DiscussionPubSub()

    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    async def on_post(msg: Any) -> None:
        # Persist immediately so polling clients see the same data the WS does.
        async with session_scope() as session:
            session.add(
                AgentMessageModel(
                    id=msg.id,
                    discussion_id=did,
                    agent_id=msg.agent_id,
                    persona_id=msg.persona_id,
                    role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    content=msg.content,
                    evidence_refs=[ref.model_dump(mode="json") for ref in msg.evidence_refs],
                    parent_message_id=msg.parent_message_id,
                    created_at=msg.created_at,
                )
            )
        await pubsub.publish(
            discussion_id,
            {
                "event": "post",
                "agent_message": msg.model_dump(mode="json"),
                "ts": _now_iso(),
            },
        )

    async def on_status(agent_id: str, state: str, extra: dict) -> None:
        await pubsub.publish(
            discussion_id,
            {
                "event": "status",
                "agent_id": agent_id,
                "state": state,
                "extra": extra,
                "ts": _now_iso(),
            },
        )

    async def on_phase(phase: str) -> None:
        # Mirror phase into the DB row's status so polling sees the transition.
        async with session_scope() as session:
            row = await session.get(DiscussionRunModel, did)
            if row is not None:
                row.status = phase
        await pubsub.publish(
            discussion_id,
            {"event": "phase", "phase": phase, "ts": _now_iso()},
        )

    async def on_claim(claim: Any) -> None:
        await pubsub.publish(
            discussion_id,
            {
                "event": "claim",
                "claim": claim.model_dump(mode="json"),
                "ts": _now_iso(),
            },
        )

    try:
        orchestrator = _build_orchestrator(
            retriever,
            on_post=on_post,
            on_status=on_status,
            on_phase=on_phase,
            on_claim=on_claim,
        )
        state = await orchestrator.run(topic, vertical=vertical, discussion_id=did)
    finally:
        await pubsub.close()

    persona_ids = [str(p.id) for p in state.personas]
    final_claim_ids = [str(c.id) for c in state.final_claims]

    # Messages are persisted live by the on_post callback above; the orchestrator's
    # on_phase callback already flips status to "synthesizing" / "completed". Just
    # stage the persona + final-claim ids for downstream consumers.
    async with session_scope() as session:
        row = await _load_discussion(session, discussion_id)
        row.persona_ids = persona_ids
        row.final_claim_ids = final_claim_ids

    # Activity boundaries are dict-only, so persist_results gets the serialized
    # final_claims via this return value rather than re-running the graph.
    serialized_claims = [c.model_dump(mode="json") for c in state.final_claims]

    logger.info(
        "run_discussion_graph",
        discussion_id=discussion_id,
        n_messages=len(state.messages),
        n_claims=len(state.final_claims),
        n_personas=len(state.personas),
    )
    return {
        "discussion_id": discussion_id,
        "n_messages": len(state.messages),
        "n_claims": len(state.final_claims),
        "final_claims": serialized_claims,
    }


@activity.defn
async def persist_results(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist final_claims as ClaimModel rows. Update discussion.status
    to "completed" and set completed_at. Return {n_claims_persisted}."""
    discussion_id = str(payload["discussion_id"])
    raw_claims = payload.get("final_claims") or []

    async with session_scope() as session:
        row = await _load_discussion(session, discussion_id)
        n_persisted = 0
        for claim_dict in raw_claims:
            try:
                cid = UUID(str(claim_dict["id"]))
            except (KeyError, ValueError):
                cid = uuid4()

            session.add(
                ClaimModel(
                    id=cid,
                    statement=str(claim_dict.get("statement", "")),
                    status=str(claim_dict.get("status", "unverified")),
                    confidence=float(claim_dict.get("confidence", 0.0)),
                    supporting_evidence=list(claim_dict.get("supporting_evidence", [])),
                    contradicting_evidence=list(
                        claim_dict.get("contradicting_evidence", [])
                    ),
                    affected_entities=[
                        str(e) for e in claim_dict.get("affected_entities", [])
                    ],
                    agent_consensus=dict(claim_dict.get("agent_consensus", {})),
                )
            )
            n_persisted += 1

        row.status = DiscussionStatus.COMPLETED.value
        row.completed_at = datetime.now(UTC)
        row.error = None

    logger.info(
        "persist_results",
        discussion_id=discussion_id,
        n_claims_persisted=n_persisted,
    )
    return {"discussion_id": discussion_id, "n_claims_persisted": n_persisted}


@activity.defn
async def _mark_failed(payload: dict[str, Any]) -> dict[str, Any]:
    """Set a discussion's status to FAILED and capture the error message."""
    discussion_id = str(payload["id"])
    error = str(payload.get("error", "unknown error"))
    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, UUID(discussion_id))
        if row is None:
            logger.warning("mark_failed.missing_row", discussion_id=discussion_id)
            return {"discussion_id": discussion_id, "marked": False}
        row.status = DiscussionStatus.FAILED.value
        row.error = error[:4096]
        row.completed_at = datetime.now(UTC)
    logger.info("mark_failed", discussion_id=discussion_id, error=error)
    return {"discussion_id": discussion_id, "marked": True}
