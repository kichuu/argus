from typing import Annotated, Any
from uuid import UUID

from argus_core.db.models import SourceModel
from argus_core.schemas import Source
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from argus_api.deps import get_session

router = APIRouter(prefix="/sources", tags=["sources"])


def _model_to_schema(row: SourceModel, *, include_text: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": row.id,
        "url": row.url,
        "feed_url": row.feed_url,
        "title": row.title,
        "content_hash": row.content_hash,
        "raw_text": row.raw_text if include_text else "",
        "fetched_at": row.fetched_at,
        "published_at": row.published_at,
        "license": row.license,
        "trust_tier": row.trust_tier,
        "publisher": row.publisher,
        "language": row.language,
    }
    if include_text:
        return Source.model_validate(payload).model_dump(mode="json")
    payload["raw_text"] = ""
    return payload


@router.get("")
async def list_sources(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_text: Annotated[bool, Query()] = False,
) -> list[dict[str, Any]]:
    stmt = (
        select(SourceModel)
        .order_by(SourceModel.fetched_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_schema(r, include_text=include_text) for r in rows]


@router.get("/{source_id}")
async def get_source(
    source_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_text: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    row = await session.get(SourceModel, source_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="source not found")
    return _model_to_schema(row, include_text=include_text)
