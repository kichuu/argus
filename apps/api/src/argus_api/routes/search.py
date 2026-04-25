"""Cross-entity search route.

Powers the Command Palette (Cmd+K). Hits Postgres ILIKE across
claims / sources / entities / discussions. No fishing on empty input —
queries shorter than 2 chars return empty.

Bind params (``.ilike(f"%{q}%")``) flow through SQLAlchemy as parameters,
not string concatenation, so this is safe from injection.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from argus_core.db.models import (
    ClaimModel,
    DiscussionRunModel,
    EntityModel,
    SourceModel,
)
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

logger = get_logger(__name__)

router = APIRouter(tags=["search"])

Kind = Literal["claims", "sources", "entities", "discussions"]
ALL_KINDS: tuple[Kind, ...] = ("claims", "sources", "entities", "discussions")

DEFAULT_LIMIT = 5
MAX_LIMIT = 20
MIN_QUERY_LEN = 2


class SearchHit(BaseModel):
    id: str
    label: str
    snippet: str
    href: str


class SearchResultsBuckets(BaseModel):
    claims: list[SearchHit] = []
    sources: list[SearchHit] = []
    entities: list[SearchHit] = []
    discussions: list[SearchHit] = []


class SearchResponse(BaseModel):
    q: str
    results: SearchResultsBuckets
    total: int


def _truncate(text: str | None, n: int) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= n else text[:n]


def _parse_kinds(raw: str | None) -> list[Kind]:
    if not raw:
        return list(ALL_KINDS)
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    valid: list[Kind] = []
    for p in parts:
        if p in ALL_KINDS:
            valid.append(p)  # type: ignore[arg-type]
    return valid or list(ALL_KINDS)


def _claim_to_hit(row: ClaimModel) -> SearchHit:
    statement = row.statement or ""
    return SearchHit(
        id=str(row.id),
        label=_truncate(statement, 60),
        snippet=_truncate(statement, 120),
        href="/synthesis",
    )


def _source_to_hit(row: SourceModel) -> SearchHit:
    publisher = row.publisher or "unknown"
    snippet = f"{publisher} · trust tier {row.trust_tier}"
    return SearchHit(
        id=str(row.id),
        label=_truncate(row.title, 60),
        snippet=snippet,
        href="/sources",
    )


def _entity_to_hit(row: EntityModel) -> SearchHit:
    return SearchHit(
        id=str(row.id),
        label=_truncate(row.canonical_name, 60),
        snippet=row.entity_type or "",
        href="/kg",
    )


def _discussion_to_hit(row: DiscussionRunModel) -> SearchHit:
    topic = row.topic or ""
    snippet = f"{row.status} · {_truncate(topic, 100)}"
    return SearchHit(
        id=str(row.id),
        label=_truncate(topic, 60),
        snippet=snippet,
        href="/synthesis",
    )


@router.get("/search", response_model=SearchResponse)
async def search(
    q: Annotated[str, Query()] = "",
    kinds: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> SearchResponse:
    q_clean = (q or "").strip()
    selected = _parse_kinds(kinds)
    empty = SearchResponse(q=q_clean, results=SearchResultsBuckets(), total=0)

    if len(q_clean) < MIN_QUERY_LEN:
        return empty

    pattern = f"%{q_clean}%"
    buckets = SearchResultsBuckets()

    async with session_scope() as session:
        if "claims" in selected:
            stmt = (
                select(ClaimModel)
                .where(ClaimModel.statement.ilike(pattern))
                .order_by(ClaimModel.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            buckets.claims = [_claim_to_hit(r) for r in rows]

        if "sources" in selected:
            stmt = (
                select(SourceModel)
                .where(
                    or_(
                        SourceModel.title.ilike(pattern),
                        SourceModel.publisher.ilike(pattern),
                    )
                )
                .order_by(SourceModel.fetched_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            buckets.sources = [_source_to_hit(r) for r in rows]

        if "entities" in selected:
            # array_to_string(aliases, ' ') ILIKE pattern  → matches any alias.
            aliases_joined = func.array_to_string(EntityModel.aliases, " ")
            stmt = (
                select(EntityModel)
                .where(
                    or_(
                        EntityModel.canonical_name.ilike(pattern),
                        aliases_joined.ilike(pattern),
                    )
                )
                .order_by(EntityModel.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            buckets.entities = [_entity_to_hit(r) for r in rows]

        if "discussions" in selected:
            stmt = (
                select(DiscussionRunModel)
                .where(DiscussionRunModel.topic.ilike(pattern))
                .order_by(DiscussionRunModel.started_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            buckets.discussions = [_discussion_to_hit(r) for r in rows]

    total = (
        len(buckets.claims)
        + len(buckets.sources)
        + len(buckets.entities)
        + len(buckets.discussions)
    )
    logger.info(
        "search.query q=%r kinds=%s total=%d", q_clean, ",".join(selected), total
    )
    return SearchResponse(q=q_clean, results=buckets, total=total)


# Re-export response model so test files can import the type cleanly.
__all__ = ["router", "SearchHit", "SearchResponse", "SearchResultsBuckets"]


# Silence unused-uuid warning if linter complains; UUID kept available for typing.
_ = UUID
