from datetime import datetime
from typing import Annotated
from uuid import UUID

from argus_core.db.models import EntityModel
from argus_core.db.session import session_scope
from argus_core.schemas import EntityType
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

router = APIRouter(prefix="/entities", tags=["entities"])


class EntityOut(BaseModel):
    id: UUID
    name: str | None = None
    type: str | None = None
    canonical_name: str | None = None


class EntityDetail(BaseModel):
    id: UUID
    name: str | None = None
    type: str | None = None
    canonical_name: str
    entity_type: str
    wikidata_id: str | None = None
    aliases: list[str] = []
    description: str | None = None
    created_at: datetime
    updated_at: datetime


def _to_summary(row: EntityModel) -> EntityOut:
    return EntityOut(
        id=row.id,
        name=row.canonical_name,
        type=row.entity_type,
        canonical_name=row.canonical_name,
    )


def _to_detail(row: EntityModel) -> EntityDetail:
    return EntityDetail(
        id=row.id,
        name=row.canonical_name,
        type=row.entity_type,
        canonical_name=row.canonical_name,
        entity_type=row.entity_type,
        wikidata_id=row.wikidata_id,
        aliases=list(row.aliases or []),
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[EntityOut])
async def list_entities(
    type_filter: Annotated[EntityType | None, Query(alias="type")] = None,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[EntityOut]:
    async with session_scope() as session:
        stmt = (
            select(EntityModel)
            .order_by(EntityModel.canonical_name)
            .limit(limit)
        )
        if type_filter is not None:
            stmt = stmt.where(EntityModel.entity_type == type_filter.value)
        if q:
            stmt = stmt.where(EntityModel.canonical_name.ilike(f"%{q}%"))
        rows = (await session.execute(stmt)).scalars().all()

    return [_to_summary(r) for r in rows]


@router.get("/{entity_id}", response_model=EntityDetail)
async def get_entity(entity_id: UUID) -> EntityDetail:
    async with session_scope() as session:
        row = await session.get(EntityModel, entity_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="entity not found"
            )
        return _to_detail(row)
