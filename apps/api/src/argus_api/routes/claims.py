from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from argus_core.db.models import ClaimModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from argus_core.schemas import ClaimStatus
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])


class ClaimOut(BaseModel):
    id: UUID
    text: str | None = None
    subject: str | None = ""
    predicate: str | None = ""
    object: str | None = ""
    confidence: float | None = None
    created_at: datetime | None = None
    source_id: str | None = None


class ClaimDetail(BaseModel):
    id: UUID
    text: str | None = None
    subject: str | None = ""
    predicate: str | None = ""
    object: str | None = ""
    statement: str
    status: str
    confidence: float
    supporting_evidence: list[dict[str, Any]] = []
    contradicting_evidence: list[dict[str, Any]] = []
    affected_entities: list[str] = []
    agent_consensus: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    source_id: str | None = None


def _first_source_id(supporting_evidence: list[dict[str, Any]] | None) -> str | None:
    if not supporting_evidence:
        return None
    first = supporting_evidence[0]
    if not isinstance(first, dict):
        return None
    src = first.get("source_id")
    return str(src) if src is not None else None


def _to_summary(row: ClaimModel) -> ClaimOut:
    return ClaimOut(
        id=row.id,
        text=row.statement,
        subject="",
        predicate="",
        object="",
        confidence=row.confidence,
        created_at=row.created_at,
        source_id=_first_source_id(row.supporting_evidence),
    )


def _to_detail(row: ClaimModel) -> ClaimDetail:
    return ClaimDetail(
        id=row.id,
        text=row.statement,
        subject="",
        predicate="",
        object="",
        statement=row.statement,
        status=row.status,
        confidence=row.confidence,
        supporting_evidence=list(row.supporting_evidence or []),
        contradicting_evidence=list(row.contradicting_evidence or []),
        affected_entities=list(row.affected_entities or []),
        agent_consensus=dict(row.agent_consensus or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
        source_id=_first_source_id(row.supporting_evidence),
    )


@router.get("", response_model=list[ClaimOut])
async def list_claims(
    status_filter: Annotated[ClaimStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[ClaimOut]:
    async with session_scope() as session:
        stmt = (
            select(ClaimModel)
            .order_by(ClaimModel.created_at.desc())
            .limit(limit)
        )
        if status_filter is not None:
            stmt = stmt.where(ClaimModel.status == status_filter.value)
        rows = (await session.execute(stmt)).scalars().all()

    return [_to_summary(r) for r in rows]


@router.get("/{claim_id}", response_model=ClaimDetail)
async def get_claim(claim_id: UUID) -> ClaimDetail:
    async with session_scope() as session:
        row = await session.get(ClaimModel, claim_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="claim not found"
            )
        return _to_detail(row)


@router.get("/{claim_id}/evidence", response_model=list[dict[str, Any]])
async def get_claim_evidence(claim_id: UUID) -> list[dict[str, Any]]:
    async with session_scope() as session:
        row = await session.get(ClaimModel, claim_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="claim not found"
            )
        return list(row.supporting_evidence or [])
