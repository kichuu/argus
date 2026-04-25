from typing import Annotated
from uuid import UUID

from argus_core.db.models import ClaimModel, EntityModel
from argus_core.logging import get_logger
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/world", tags=["world"])


class PlacePin(BaseModel):
    entity_id: UUID
    name: str
    lat: float
    lon: float
    wikidata_id: str | None
    claim_count: int


@router.get("/places", response_model=list[PlacePin])
async def list_places(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(200, ge=1, le=2000),
    min_claim_count: int = Query(0, ge=0),
) -> list[PlacePin]:
    """Places with non-null coords + count of claims that mention them."""
    # Correlated scalar subquery: count claims whose affected_entities array
    # contains the entity id (cast to text since affected_entities is text[]).
    entity_id_text = cast(EntityModel.id, String)
    claim_count_sq = (
        select(func.count(ClaimModel.id))
        .where(entity_id_text == func.any(ClaimModel.affected_entities))
        .correlate(EntityModel)
        .scalar_subquery()
    )

    stmt = (
        select(
            EntityModel.id,
            EntityModel.canonical_name,
            EntityModel.latitude,
            EntityModel.longitude,
            EntityModel.wikidata_id,
            claim_count_sq.label("claim_count"),
        )
        .where(
            EntityModel.entity_type == "place",
            EntityModel.latitude.is_not(None),
            EntityModel.longitude.is_not(None),
        )
        .order_by(claim_count_sq.desc(), EntityModel.canonical_name.asc())
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()
    pins: list[PlacePin] = []
    for row in rows:
        count = int(row.claim_count or 0)
        if count < min_claim_count:
            continue
        pins.append(
            PlacePin(
                entity_id=row.id,
                name=row.canonical_name,
                lat=row.latitude,
                lon=row.longitude,
                wikidata_id=row.wikidata_id,
                claim_count=count,
            )
        )
    return pins
