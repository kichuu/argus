"""Recent system activity feed for the shell NotifsPanel.

Derives a chronologically merged event stream from existing tables — claims,
sources, and discussion runs — with no separate event store. Read-only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from argus_core.db.models import ClaimModel, DiscussionRunModel, SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(tags=["activity"])


EventKind = Literal["claim", "source", "discussion"]


class ActivityEvent(BaseModel):
    id: str
    kind: EventKind
    title: str
    summary: str
    ts: datetime
    href: str


class ActivityResponse(BaseModel):
    events: list[ActivityEvent]


def _truncate(text: str, n: int = 140) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


@router.get("/activity", response_model=ActivityResponse)
async def activity(
    limit: int = Query(20, ge=1, le=100),
) -> ActivityResponse:
    async with session_scope() as session:
        claim_rows = (
            (
                await session.execute(
                    select(ClaimModel)
                    .order_by(ClaimModel.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        source_rows = (
            (
                await session.execute(
                    select(SourceModel)
                    .order_by(SourceModel.fetched_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        discussion_rows = (
            (
                await session.execute(
                    select(DiscussionRunModel)
                    .order_by(DiscussionRunModel.started_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    events: list[ActivityEvent] = []

    for c in claim_rows:
        if c.created_at is None:
            continue
        events.append(
            ActivityEvent(
                id=f"claim:{c.id}",
                kind="claim",
                title=_truncate(c.statement or "untitled claim", 100),
                summary=(c.status or "unverified").replace("_", " "),
                ts=c.created_at,
                href="/synthesis",
            )
        )

    for s in source_rows:
        if s.fetched_at is None:
            continue
        events.append(
            ActivityEvent(
                id=f"source:{s.id}",
                kind="source",
                title=_truncate(s.title or s.url or "source", 100),
                summary=s.publisher or s.feed_url or s.url or "",
                ts=s.fetched_at,
                href="/sources",
            )
        )

    for d in discussion_rows:
        ts = d.completed_at or d.started_at
        if ts is None:
            continue
        n_claims = len(d.final_claim_ids or [])
        if d.status == "completed":
            summary = f"completed · {n_claims} claim{'s' if n_claims != 1 else ''}"
        elif d.status == "failed":
            summary = "failed"
        else:
            summary = d.status or "running"
        events.append(
            ActivityEvent(
                id=f"discussion:{d.id}",
                kind="discussion",
                title=_truncate(d.topic or "discussion", 100),
                summary=summary,
                ts=ts,
                href="/synthesis",
            )
        )

    events.sort(key=lambda e: e.ts, reverse=True)
    return ActivityResponse(events=events[:limit])
