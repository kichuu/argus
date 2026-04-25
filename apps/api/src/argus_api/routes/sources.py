from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from argus_core.db.models import SourceModel
from argus_core.db.session import session_scope
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

router = APIRouter(prefix="/sources", tags=["sources"])

SourceStatus = Literal["ok", "warn", "down"]
SourceType = Literal["rss", "api", "manual"]


def _derive_type(row: SourceModel) -> SourceType:
    if row.feed_url:
        return "rss"
    if row.url:
        return "api"
    return "manual"


def _derive_status(row: SourceModel) -> SourceStatus:
    # No real status tracking yet — stub to "ok" per spec.
    return "ok"


def _derive_name(row: SourceModel) -> str | None:
    return row.title or row.publisher


class SourceOut(BaseModel):
    id: UUID
    name: str | None = None
    type: SourceType | None = None
    status: SourceStatus | None = None


class SourceDetail(BaseModel):
    id: UUID
    name: str | None = None
    type: SourceType | None = None
    status: SourceStatus | None = None
    url: str | None = None
    feed_url: str | None = None
    title: str
    content_hash: str
    raw_text_length: int
    fetched_at: datetime
    published_at: datetime | None = None
    license: str | None = None
    trust_tier: int
    publisher: str | None = None
    language: str | None = None


def _to_summary(row: SourceModel) -> SourceOut:
    return SourceOut(
        id=row.id,
        name=_derive_name(row),
        type=_derive_type(row),
        status=_derive_status(row),
    )


def _to_detail(row: SourceModel) -> SourceDetail:
    return SourceDetail(
        id=row.id,
        name=_derive_name(row),
        type=_derive_type(row),
        status=_derive_status(row),
        url=row.url,
        feed_url=row.feed_url,
        title=row.title,
        content_hash=row.content_hash,
        raw_text_length=len(row.raw_text or ""),
        fetched_at=row.fetched_at,
        published_at=row.published_at,
        license=row.license,
        trust_tier=row.trust_tier,
        publisher=row.publisher,
        language=row.language,
    )


@router.get("", response_model=list[SourceOut])
async def list_sources(
    status_filter: Annotated[SourceStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[SourceOut]:
    async with session_scope() as session:
        stmt = (
            select(SourceModel)
            .order_by(SourceModel.fetched_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()

    summaries = [_to_summary(r) for r in rows]
    if status_filter is not None:
        summaries = [s for s in summaries if s.status == status_filter]
    return summaries


@router.get("/{source_id}", response_model=SourceDetail)
async def get_source(source_id: UUID) -> SourceDetail:
    async with session_scope() as session:
        row = await session.get(SourceModel, source_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="source not found"
            )
        return _to_detail(row)
