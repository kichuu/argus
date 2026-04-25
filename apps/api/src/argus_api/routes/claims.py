from typing import Annotated
from uuid import UUID

from argus_core.db.models import ClaimModel
from argus_core.logging import get_logger
from argus_core.schemas import Claim, EvidenceRef
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])


def _model_to_schema(row: ClaimModel) -> Claim:
    return Claim.model_validate(
        {
            "id": row.id,
            "statement": row.statement,
            "status": row.status,
            "confidence": row.confidence,
            "supporting_evidence": row.supporting_evidence,
            "contradicting_evidence": row.contradicting_evidence,
            "affected_entities": row.affected_entities,
            "agent_consensus": row.agent_consensus or {},
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


@router.get("")
async def list_claims(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Claim]:
    stmt = (
        select(ClaimModel)
        .order_by(ClaimModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_schema(r) for r in rows]


@router.get("/{claim_id}")
async def get_claim(
    claim_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Claim:
    row = await session.get(ClaimModel, claim_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="claim not found")
    return _model_to_schema(row)


@router.get("/{claim_id}/evidence")
async def get_claim_evidence(
    claim_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[EvidenceRef]:
    row = await session.get(ClaimModel, claim_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="claim not found")
    return [EvidenceRef.model_validate(e) for e in (row.supporting_evidence or [])]


# TODO(auth): gate POST /claims behind service-to-service auth before exposing externally.
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_claim(
    claim: Claim,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Claim:
    row = ClaimModel(
        id=claim.id,
        statement=claim.statement,
        status=claim.status.value,
        confidence=claim.confidence,
        supporting_evidence=[e.model_dump(mode="json") for e in claim.supporting_evidence],
        contradicting_evidence=[e.model_dump(mode="json") for e in claim.contradicting_evidence],
        affected_entities=[str(e) for e in claim.affected_entities],
        agent_consensus=claim.agent_consensus.model_dump(),
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )
    session.add(row)
    await session.flush()
    return _model_to_schema(row)
