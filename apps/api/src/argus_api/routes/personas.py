from datetime import datetime
from typing import Annotated
from uuid import UUID

from argus_core.db.models import PersonaModel
from argus_core.db.session import session_scope
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaOut(BaseModel):
    id: UUID
    frame: str
    description: str
    knowledge_emphasis: list[str] = []
    created_at: datetime


class PersonaCreate(BaseModel):
    frame: str = Field(min_length=3, max_length=120)
    description: str
    knowledge_emphasis: list[str] = Field(default_factory=list)


def _to_out(row: PersonaModel) -> PersonaOut:
    return PersonaOut(
        id=row.id,
        frame=row.frame,
        description=row.description,
        knowledge_emphasis=list(row.knowledge_emphasis or []),
        created_at=row.created_at,
    )


@router.get("", response_model=list[PersonaOut])
async def list_personas(
    frame: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[PersonaOut]:
    async with session_scope() as session:
        stmt = (
            select(PersonaModel)
            .order_by(PersonaModel.created_at.desc())
            .limit(limit)
        )
        if frame:
            stmt = stmt.where(PersonaModel.frame.ilike(f"%{frame}%"))
        rows = (await session.execute(stmt)).scalars().all()

    return [_to_out(r) for r in rows]


@router.get("/{persona_id}", response_model=PersonaOut)
async def get_persona(persona_id: UUID) -> PersonaOut:
    async with session_scope() as session:
        row = await session.get(PersonaModel, persona_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="persona not found"
            )
        return _to_out(row)


@router.post("", response_model=PersonaOut, status_code=status.HTTP_201_CREATED)
async def create_persona(body: PersonaCreate) -> PersonaOut:
    async with session_scope() as session:
        row = PersonaModel(
            frame=body.frame,
            description=body.description,
            knowledge_emphasis=list(body.knowledge_emphasis),
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return _to_out(row)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(persona_id: UUID) -> None:
    async with session_scope() as session:
        row = await session.get(PersonaModel, persona_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="persona not found"
            )
        await session.delete(row)
    return None
