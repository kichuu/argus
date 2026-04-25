from typing import Annotated, Any
from uuid import UUID

from argus_core.db.models import EntityModel, RelationModel
from argus_core.schemas import Entity, EntityType
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session

router = APIRouter(prefix="/entities", tags=["entities"])


def _model_to_schema(row: EntityModel) -> Entity:
    return Entity.model_validate(
        {
            "id": row.id,
            "canonical_name": row.canonical_name,
            "entity_type": row.entity_type,
            "wikidata_id": row.wikidata_id,
            "aliases": row.aliases or [],
            "description": row.description,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


@router.get("")
async def list_entities(
    session: Annotated[AsyncSession, Depends(get_session)],
    entity_type: Annotated[EntityType | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Entity]:
    stmt = select(EntityModel).order_by(EntityModel.canonical_name).limit(limit).offset(offset)
    if entity_type is not None:
        stmt = stmt.where(EntityModel.entity_type == entity_type.value)
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_schema(r) for r in rows]


@router.get("/{entity_id}")
async def get_entity(
    entity_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Entity:
    row = await session.get(EntityModel, entity_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entity not found")
    return _model_to_schema(row)


@router.get("/{entity_id}/relations")
async def get_entity_relations(
    entity_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, Any]]:
    # TODO(graph): once AGE is wired in argus-retrieval, swap this direct relations query
    # for a multi-hop traversal API.
    stmt = (
        select(RelationModel)
        .where(
            (RelationModel.subject_id == entity_id) | (RelationModel.object_id == entity_id)
        )
        .order_by(RelationModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(r.id),
            "subject_id": str(r.subject_id),
            "relation_type": r.relation_type,
            "object_id": str(r.object_id),
            "confidence": r.confidence,
            "valid_from": r.valid_from,
            "valid_to": r.valid_to,
            "evidence": r.evidence or [],
            "created_at": r.created_at,
        }
        for r in rows
    ]
