from typing import Any
from uuid import UUID, uuid4

from temporalio import activity

from argus_core.db.models import DiscussionRunModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import DiscussionStatus

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


@activity.defn
async def assemble_evidence_pack(discussion_id: str) -> dict[str, Any]:
    # TODO(retrieval): use argus_retrieval to build a vertical-scoped evidence pack
    # (vector + graph hops) and persist into DiscussionRunModel.evidence_pack.
    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, UUID(discussion_id))
        if row is not None:
            row.status = DiscussionStatus.RESEARCHING.value
    logger.info("assemble_evidence_pack.stub", discussion_id=discussion_id)
    return {"discussion_id": discussion_id, "evidence_count": 0}


@activity.defn
async def run_discussion_graph(discussion_id: str) -> dict[str, Any]:
    # TODO(agents): build DiscussionGraph from argus_agents.graph using the
    # persisted evidence_pack, run the LangGraph, and return its serialized result
    # (messages, final_claim_ids). Persistence is handled by persist_results.
    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, UUID(discussion_id))
        if row is not None:
            row.status = DiscussionStatus.DEBATING.value
    logger.info("run_discussion_graph.stub", discussion_id=discussion_id)
    return {"messages": [], "final_claim_ids": []}


@activity.defn
async def persist_results(discussion_id: str, graph_result: dict[str, Any]) -> dict[str, Any]:
    # TODO(agents): persist AgentMessageModel rows from graph_result["messages"]
    # and write final_claim_ids back onto DiscussionRunModel.
    async with session_scope() as session:
        row = await session.get(DiscussionRunModel, UUID(discussion_id))
        if row is not None:
            row.final_claim_ids = list(graph_result.get("final_claim_ids", []))
            row.status = DiscussionStatus.COMPLETED.value
    logger.info(
        "persist_results",
        discussion_id=discussion_id,
        messages=len(graph_result.get("messages", [])),
    )
    return {"discussion_id": discussion_id, "persisted": True}
