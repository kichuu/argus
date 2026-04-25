"""Discussion routes — kick off, list, inspect a multi-agent debate.

Frontend contract:
- ``POST /discussions``: launch a debate. Body ``{topic, vertical?}``. Response
  ``{id, status: "planning"}``. The row is pre-created so polling works
  immediately even before Temporal/the local pipeline picks it up.
- ``GET /discussions``: list summaries for HomeScreen, filterable by status.
- ``GET /discussions/{id}``: detail (OpsTheater header / SynthesisView).
- ``GET /discussions/{id}/messages``: ordered transcript (DebateRoom).
- ``GET /discussions/{id}/claims``: final claims emitted by the synthesizer.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from argus_core.db.models import (
    AgentMessageModel,
    ClaimModel,
    DiscussionRunModel,
)
from argus_core.logging import get_logger
from argus_core.schemas import DiscussionStatus
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session
from argus_api.temporal_client import DiscussionLauncher, get_launcher

logger = get_logger(__name__)

router = APIRouter(prefix="/discussions", tags=["discussions"])


# --- request / response models ------------------------------------------------


class StartDiscussionBody(BaseModel):
    topic: str = Field(min_length=1)
    # Default matches the committed vertical in config/vertical.yaml.
    vertical: str = "geopolitics"
    # Forward-compat run params. Master/research agents will read these once
    # upgraded; for now we accept + log them so the wiring is verifiable from
    # the frontend.
    depth: Literal["quick", "standard", "deep"] = "standard"
    source_kinds: list[Literal["rss", "news", "social", "kg"]] = Field(
        default_factory=lambda: ["rss", "news"]
    )
    auto_personas: bool = True


class StartDiscussionResponse(BaseModel):
    id: UUID
    status: str


class DiscussionSummary(BaseModel):
    id: UUID
    topic: str
    vertical: str
    status: str
    created_at: datetime  # mapped from DiscussionRunModel.started_at


class DiscussionDetail(BaseModel):
    id: UUID
    topic: str
    vertical: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    evidence_pack_count: int
    final_claim_ids_count: int
    error: str | None = None


class AgentMessageOut(BaseModel):
    id: UUID
    discussion_id: UUID
    agent_id: str
    persona_id: UUID | None
    role: str
    content: str
    evidence_refs: list[dict[str, Any]]
    parent_message_id: UUID | None
    created_at: datetime


# --- helpers ------------------------------------------------------------------


def _row_to_summary(row: DiscussionRunModel) -> DiscussionSummary:
    return DiscussionSummary(
        id=row.id,
        topic=row.topic,
        vertical=row.vertical,
        status=row.status,
        created_at=row.started_at,
    )


def _row_to_message(row: AgentMessageModel) -> AgentMessageOut:
    return AgentMessageOut(
        id=row.id,
        discussion_id=row.discussion_id,
        agent_id=row.agent_id,
        persona_id=row.persona_id,
        role=row.role,
        content=row.content,
        evidence_refs=list(row.evidence_refs or []),
        parent_message_id=row.parent_message_id,
        created_at=row.created_at,
    )


# --- routes -------------------------------------------------------------------


@router.post("", response_model=StartDiscussionResponse)
async def start_discussion(
    body: StartDiscussionBody,
    session: Annotated[AsyncSession, Depends(get_session)],
    launcher: Annotated[DiscussionLauncher, Depends(get_launcher)],
) -> StartDiscussionResponse:
    """Pre-create the run row, then hand off to the launcher.

    The row exists with status=planning before we return so a fast polling
    client can hit ``GET /discussions/{id}`` immediately.
    """
    discussion_id = uuid4()
    # NOTE: depth / source_kinds / auto_personas accepted but not yet acted on.
    # DiscussionRunModel has no free-form JSONB column to stash them in, so
    # we log them at info level and rely on the agents to read them off the
    # body once they're upgraded to honor run-time controls.
    logger.info(
        "discussion.start.params depth=%s sources=%s auto_personas=%s",
        body.depth,
        body.source_kinds,
        body.auto_personas,
    )
    row = DiscussionRunModel(
        id=discussion_id,
        topic=body.topic,
        vertical=body.vertical,
        status=DiscussionStatus.PLANNING.value,
    )
    session.add(row)
    await session.flush()

    await launcher.start(body.topic, body.vertical, str(discussion_id))

    return StartDiscussionResponse(
        id=discussion_id,
        status=DiscussionStatus.PLANNING.value,
    )


@router.get("", response_model=list[DiscussionSummary])
async def list_discussions(
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[DiscussionSummary]:
    stmt = select(DiscussionRunModel).order_by(DiscussionRunModel.started_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(DiscussionRunModel.status == status_filter)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_summary(r) for r in rows]


@router.get("/{discussion_id}", response_model=DiscussionDetail)
async def get_discussion(
    discussion_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiscussionDetail:
    row = await session.get(DiscussionRunModel, discussion_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="discussion not found",
        )
    return DiscussionDetail(
        id=row.id,
        topic=row.topic,
        vertical=row.vertical,
        status=row.status,
        started_at=row.started_at,
        completed_at=row.completed_at,
        evidence_pack_count=len(row.evidence_pack or []),
        final_claim_ids_count=len(row.final_claim_ids or []),
        error=row.error,
    )


@router.get("/{discussion_id}/messages", response_model=list[AgentMessageOut])
async def get_discussion_messages(
    discussion_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AgentMessageOut]:
    exists = await session.get(DiscussionRunModel, discussion_id)
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="discussion not found",
        )
    stmt = (
        select(AgentMessageModel)
        .where(AgentMessageModel.discussion_id == discussion_id)
        .order_by(AgentMessageModel.created_at.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_message(r) for r in rows]


@router.get("/{discussion_id}/claims")
async def get_discussion_claims(
    discussion_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, Any]]:
    """Return the final ClaimModel rows referenced by ``final_claim_ids``.

    Returned as plain dicts to keep the surface flat for the frontend; the
    /claims route owns the strict ``Claim`` schema response.
    """
    row = await session.get(DiscussionRunModel, discussion_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="discussion not found",
        )

    raw_ids = row.final_claim_ids or []
    if not raw_ids:
        return []

    claim_uuids: list[UUID] = []
    for cid in raw_ids:
        try:
            claim_uuids.append(UUID(str(cid)))
        except (ValueError, TypeError):
            continue
    if not claim_uuids:
        return []

    stmt = select(ClaimModel).where(ClaimModel.id.in_(claim_uuids))
    claim_rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(c.id),
            "statement": c.statement,
            "status": c.status,
            "confidence": c.confidence,
            "supporting_evidence": list(c.supporting_evidence or []),
            "contradicting_evidence": list(c.contradicting_evidence or []),
            "affected_entities": list(c.affected_entities or []),
            "agent_consensus": c.agent_consensus or {},
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in claim_rows
    ]


# Legacy compatibility: count messages — used by some existing callers.
async def _count_messages(session: AsyncSession, discussion_id: UUID) -> int:
    stmt = select(func.count()).where(AgentMessageModel.discussion_id == discussion_id)
    return int((await session.execute(stmt)).scalar_one())
