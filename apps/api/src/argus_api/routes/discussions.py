from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from argus_core.db.models import AgentMessageModel, DiscussionRunModel
from argus_core.logging import get_logger
from argus_core.pubsub import DiscussionPubSub
from argus_core.schemas import AgentMessage, DiscussionStatus
from argus_core.settings import Settings
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session, get_settings_dep
from argus_api.temporal_client import TemporalUnavailableError, get_client

logger = get_logger(__name__)

router = APIRouter(prefix="/discussions", tags=["discussions"])
ws_router = APIRouter(tags=["discussions-ws"])


@ws_router.websocket("/ws/discussions/{discussion_id}")
async def discussion_ws(websocket: WebSocket, discussion_id: str) -> None:
    """Stream live discussion events from Redis pub/sub to the client.

    Polling fallback (`GET /discussions/{id}/messages`) keeps working when the
    WS isn't available, since each event is also persisted to the DB.
    """
    await websocket.accept()
    pubsub = DiscussionPubSub()
    try:
        async with pubsub.subscribe(discussion_id) as events:
            async for event in events:
                await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        logger.warning("discussion_ws_error", discussion_id=discussion_id, error=str(exc))
    finally:
        await pubsub.close()


class StartDiscussionBody(BaseModel):
    topic: str
    vertical: str


class StartDiscussionResponse(BaseModel):
    discussion_id: UUID
    workflow_id: str
    mode: Literal["temporal", "inline"]


class DiscussionDetail(BaseModel):
    id: UUID
    topic: str
    vertical: str
    status: DiscussionStatus
    messages_count: int
    final_claim_ids: list[UUID]
    error: str | None


class DiscussionListItem(BaseModel):
    id: UUID
    topic: str
    vertical: str
    status: DiscussionStatus
    started_at: datetime
    completed_at: datetime | None
    final_claim_count: int


class DiscussionListResponse(BaseModel):
    items: list[DiscussionListItem]
    total: int
    limit: int
    offset: int


async def _run_inline(discussion_id: str) -> None:
    """Execute the discussion pipeline directly in-process.

    Used as a BackgroundTasks fallback when Temporal isn't reachable. Calls
    the activity functions as plain async coroutines (they don't use
    `activity.heartbeat()` and tolerate execution outside a worker).
    """
    from argus_workers.activities.discussion import (
        _mark_failed,
        assemble_evidence_pack,
        persist_results,
        run_discussion_graph,
    )

    try:
        await assemble_evidence_pack(discussion_id)
        graph_result = await run_discussion_graph(discussion_id)
        await persist_results(
            {
                "discussion_id": discussion_id,
                "final_claims": graph_result.get("final_claims", []),
            }
        )
    except Exception as exc:
        logger.error("inline_discussion_failed", discussion_id=discussion_id, error=str(exc))
        try:
            await _mark_failed({"id": discussion_id, "error": str(exc)})
        except Exception as mark_exc:
            logger.error(
                "inline_mark_failed_errored",
                discussion_id=discussion_id,
                error=str(mark_exc),
            )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StartDiscussionResponse,
)
async def start_discussion(
    body: StartDiscussionBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
    background_tasks: BackgroundTasks,
) -> StartDiscussionResponse:
    discussion_id = uuid4()
    row = DiscussionRunModel(
        id=discussion_id,
        topic=body.topic,
        vertical=body.vertical,
        status=DiscussionStatus.PLANNING.value,
    )
    session.add(row)
    await session.flush()

    workflow_id = f"discussion-{discussion_id}"
    payload = {
        "topic": body.topic,
        "vertical": body.vertical,
        "discussion_id": str(discussion_id),
    }

    try:
        client = await get_client()
    except TemporalUnavailableError as exc:
        logger.info(
            "discussions.temporal_unavailable_inline_fallback",
            discussion_id=str(discussion_id),
            error=str(exc),
        )
        background_tasks.add_task(_run_inline, str(discussion_id))
        return StartDiscussionResponse(
            discussion_id=discussion_id,
            workflow_id=workflow_id,
            mode="inline",
        )

    await client.start_workflow(
        "DiscussionWorkflow",
        payload,
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return StartDiscussionResponse(
        discussion_id=discussion_id,
        workflow_id=workflow_id,
        mode="temporal",
    )


@router.get("", response_model=DiscussionListResponse)
async def list_discussions(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: DiscussionStatus | None = None,
    vertical: str | None = None,
) -> DiscussionListResponse:
    """Paginated list of discussions, newest first."""
    filters: list[Any] = []
    if status is not None:
        filters.append(DiscussionRunModel.status == status.value)
    if vertical is not None:
        filters.append(DiscussionRunModel.vertical == vertical)

    count_stmt = select(func.count()).select_from(DiscussionRunModel)
    list_stmt = select(DiscussionRunModel)
    for clause in filters:
        count_stmt = count_stmt.where(clause)
        list_stmt = list_stmt.where(clause)

    list_stmt = (
        list_stmt.order_by(DiscussionRunModel.started_at.desc()).limit(limit).offset(offset)
    )

    total = (await session.execute(count_stmt)).scalar_one()
    rows = (await session.execute(list_stmt)).scalars().all()

    items = [
        DiscussionListItem(
            id=row.id,
            topic=row.topic,
            vertical=row.vertical,
            status=DiscussionStatus(row.status),
            started_at=row.started_at,
            completed_at=row.completed_at,
            final_claim_count=len(row.final_claim_ids or []),
        )
        for row in rows
    ]
    return DiscussionListResponse(
        items=items,
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/{discussion_id}", response_model=DiscussionDetail)
async def get_discussion(
    discussion_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiscussionDetail:
    row = await session.get(DiscussionRunModel, discussion_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discussion not found")

    count_stmt = select(func.count()).where(AgentMessageModel.discussion_id == discussion_id)
    messages_count = (await session.execute(count_stmt)).scalar_one()

    return DiscussionDetail(
        id=row.id,
        topic=row.topic,
        vertical=row.vertical,
        status=DiscussionStatus(row.status),
        messages_count=int(messages_count),
        final_claim_ids=[UUID(c) for c in (row.final_claim_ids or [])],
        error=row.error,
    )


@router.get("/{discussion_id}/messages")
async def get_discussion_messages(
    discussion_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AgentMessage]:
    exists = await session.get(DiscussionRunModel, discussion_id)
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discussion not found")

    stmt = (
        select(AgentMessageModel)
        .where(AgentMessageModel.discussion_id == discussion_id)
        .order_by(AgentMessageModel.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    out: list[AgentMessage] = []
    for r in rows:
        payload: dict[str, Any] = {
            "id": r.id,
            "discussion_id": r.discussion_id,
            "agent_id": r.agent_id,
            "persona_id": r.persona_id,
            "role": r.role,
            "content": r.content,
            "evidence_refs": r.evidence_refs or [],
            "parent_message_id": r.parent_message_id,
            "created_at": r.created_at,
        }
        out.append(AgentMessage.model_validate(payload))
    return out
