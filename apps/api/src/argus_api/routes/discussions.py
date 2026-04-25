from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_core.db.models import AgentMessageModel, DiscussionRunModel
from argus_core.logging import get_logger
from argus_core.schemas import AgentMessage, DiscussionStatus
from argus_core.settings import Settings

from argus_api.deps import get_session, get_settings_dep
from argus_api.temporal_client import TemporalUnavailableError, get_client

logger = get_logger(__name__)

router = APIRouter(prefix="/discussions", tags=["discussions"])


class StartDiscussionBody(BaseModel):
    topic: str
    vertical: str


class StartDiscussionResponse(BaseModel):
    discussion_id: UUID
    workflow_id: str


class DiscussionDetail(BaseModel):
    id: UUID
    topic: str
    vertical: str
    status: DiscussionStatus
    messages_count: int
    final_claim_ids: list[UUID]
    error: str | None


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StartDiscussionResponse,
)
async def start_discussion(
    body: StartDiscussionBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
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
    try:
        client = await get_client()
        await client.start_workflow(
            "DiscussionWorkflow",
            args=[body.topic, body.vertical, str(discussion_id)],
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
    except TemporalUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"temporal unavailable: {exc}",
        ) from exc

    return StartDiscussionResponse(discussion_id=discussion_id, workflow_id=workflow_id)


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
