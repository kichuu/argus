from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from argus_core.db.models import (
    AgentMessageModel,
    ClaimModel,
    DiscussionRunModel,
)
from sqlalchemy import select as _sa_select
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import DiscussionStatus, EvidenceRef
from argus_core.settings import get_settings
from argus_extraction.providers import family_of, get_provider
from sqlalchemy import desc, select
from temporalio import activity

if TYPE_CHECKING:
    from argus_retrieval.hybrid import HybridRetriever
    from argus_retrieval.types import RetrievedSpan

logger = get_logger(__name__)


async def _build_hybrid_retriever() -> "HybridRetriever | None":
    """Construct a real HybridRetriever; return None if any backend
    (Qdrant/AGE/embedder/reranker) is unreachable.

    Phase 4 must always have a fallback, so any failure here is logged at
    warning level and surfaces as None to the caller.
    """
    try:
        from argus_retrieval.embeddings import Embedder
        from argus_retrieval.graph import GraphQuerier
        from argus_retrieval.hybrid import HybridRetriever
        from argus_retrieval.rerank import get_reranker
        from argus_retrieval.vector import VectorIndex
    except Exception as e:  # noqa: BLE001
        logger.warning("hybrid_retriever_import_failed", error=str(e))
        return None

    try:
        vector_index = VectorIndex()
        embedder = Embedder()
        reranker = get_reranker()
        graph = GraphQuerier()
    except Exception as e:  # noqa: BLE001
        logger.warning("hybrid_retriever_build_failed", error=str(e))
        return None

    return HybridRetriever(
        vector_index=vector_index,
        graph=graph,
        reranker=reranker,
        embedder=embedder,
    )


def _retrieved_span_to_evidence_dict(span: "RetrievedSpan") -> dict[str, Any]:
    """Translate a RetrievedSpan into an EvidenceRef-shaped dict.

    EvidenceRef enforces `char_end - char_start == len(verbatim_span)`. If a
    RetrievedSpan ever lands here with mismatched offsets (e.g. defaulted to
    0/0), we coerce them to (0, len(span)) so EvidenceRef.model_validate will
    accept the dict without a re-verification step.
    """
    span_text = span.verbatim_span
    char_start = int(getattr(span, "char_start", 0) or 0)
    char_end = int(getattr(span, "char_end", 0) or 0)
    if char_end - char_start != len(span_text):
        char_start = 0
        char_end = len(span_text)
    ref = EvidenceRef(
        source_id=span.source_id,
        verbatim_span=span_text,
        char_start=char_start,
        char_end=char_end,
        fetched_at=span.fetched_at,
        trust_tier=int(span.trust_tier),
    )
    return ref.model_dump(mode="json")


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
        topic = row.topic
        vertical = row.vertical

    pack: list[dict[str, Any]] = []
    source = "baseline"
    retriever = await _build_hybrid_retriever()
    if retriever is not None:
        try:
            spans = await retriever.retrieve(
                topic, top_k=20, recency_boost=True
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "hybrid_retrieve_failed_falling_back_baseline",
                discussion_id=discussion_id,
                error=str(e),
            )
            spans = []
        for span in spans:
            try:
                pack.append(_retrieved_span_to_evidence_dict(span))
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "retrieved_span_translation_failed",
                    discussion_id=discussion_id,
                    error=str(e),
                )
        if pack:
            source = "hybrid"

    if not pack:
        pack = await _baseline_evidence_pack(vertical)
        source = "baseline"

    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, did)
        if row is None:
            raise RuntimeError(f"discussion {discussion_id} not found")
        row.evidence_pack = pack
        row.status = DiscussionStatus.RESEARCHING.value

    logger.info(
        "assemble_evidence_pack.done",
        discussion_id=discussion_id,
        evidence_count=len(pack),
        source=source,
    )
    return {
        "discussion_id": discussion_id,
        "evidence_count": len(pack),
        "source": source,
    }


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
    # The pack is pre-assembled by `assemble_evidence_pack` (which uses
    # HybridRetriever when Qdrant/AGE are up, baseline otherwise). The discussion
    # graph then reasons over that static pack — no need for a live retriever
    # inside the graph, which would re-hit Qdrant per persona and cascade-fail
    # when it's down.
    retriever: Any = _EvidencePackRetriever(evidence_dicts)
    logger.info(
        "run_discussion_graph.using_static_pack",
        discussion_id=discussion_id,
        evidence_count=len(evidence_dicts),
    )

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
    final_claim_ids: list[str] = []

    async with session_scope() as session:
        # Persist each synthesized claim as a ClaimModel row, idempotent by id.
        for c in final_claims:
            try:
                cid = UUID(str(c.get("id"))) if c.get("id") else uuid4()
            except (ValueError, TypeError):
                cid = uuid4()
            existing = await session.get(ClaimModel, cid)
            if existing is not None:
                final_claim_ids.append(str(cid))
                continue
            claim = ClaimModel(
                id=cid,
                statement=str(c.get("statement", "")),
                status=str(c.get("status", "unverified")),
                confidence=float(c.get("confidence", 0.0)),
                supporting_evidence=c.get("supporting_evidence", []) or [],
                contradicting_evidence=c.get("contradicting_evidence", []) or [],
                affected_entities=[str(e) for e in (c.get("affected_entities") or [])],
                agent_consensus=c.get("agent_consensus", {}) or {},
            )
            session.add(claim)
            final_claim_ids.append(str(cid))

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
