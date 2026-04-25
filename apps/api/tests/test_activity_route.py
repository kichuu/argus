"""Tests for /activity — recent system events merged from claims, sources,
and discussion runs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from argus_api.main import app
from argus_api.routes import activity as activity_route
from httpx import ASGITransport, AsyncClient


class _Result:
    def __init__(self, items: list) -> None:
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _Session:
    """Routes incoming SELECTs by FROM-table to the right canned list."""

    def __init__(self, *, claims: list, sources: list, discussions: list) -> None:
        self.claims = claims
        self.sources = sources
        self.discussions = discussions

    async def execute(self, stmt):
        try:
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()
        except Exception:
            sql = str(stmt).lower()
        if "discussion_runs" in sql:
            return _Result(self.discussions)
        if "claims" in sql:
            return _Result(self.claims)
        if "sources" in sql:
            return _Result(self.sources)
        return _Result([])

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _scope_factory(session: _Session):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


# ---------- Row builders ----------


def _claim(offset_min: int = 5, status: str = "likely_true", text: str = "x"):
    return SimpleNamespace(
        id=uuid4(),
        statement=text,
        status=status,
        created_at=datetime.now(UTC) - timedelta(minutes=offset_min),
    )


def _source(offset_min: int = 10, title: str = "headline", publisher: str = "BBC"):
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        publisher=publisher,
        url="https://example.com/x",
        feed_url=None,
        fetched_at=datetime.now(UTC) - timedelta(minutes=offset_min),
    )


def _discussion(
    offset_min: int = 15,
    status: str = "completed",
    final_claim_ids: list[str] | None = None,
):
    started = datetime.now(UTC) - timedelta(minutes=offset_min)
    completed = started + timedelta(minutes=2) if status == "completed" else None
    return SimpleNamespace(
        id=uuid4(),
        topic="taiwan strait",
        status=status,
        started_at=started,
        completed_at=completed,
        final_claim_ids=final_claim_ids or [],
    )


# ---------- Tests ----------


@pytest.mark.asyncio
async def test_activity_merges_and_sorts(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _Session(
        claims=[_claim(offset_min=2), _claim(offset_min=20, text="older")],
        sources=[_source(offset_min=5)],
        discussions=[_discussion(offset_min=8, final_claim_ids=["a", "b", "c"])],
    )
    monkeypatch.setattr(activity_route, "session_scope", _scope_factory(sess))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/activity?limit=10")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "events" in body
    events = body["events"]
    assert len(events) == 4
    # Newest first.
    timestamps = [e["ts"] for e in events]
    assert timestamps == sorted(timestamps, reverse=True)

    # Shape check: every event has the expected keys.
    for e in events:
        assert {"id", "kind", "title", "summary", "ts", "href"} <= set(e.keys())
        assert e["kind"] in {"claim", "source", "discussion"}
        assert e["href"].startswith("/")

    # Discussion summary has claim count.
    disc = next(e for e in events if e["kind"] == "discussion")
    assert "3 claims" in disc["summary"]
    assert disc["href"] == "/synthesis"

    src = next(e for e in events if e["kind"] == "source")
    assert src["href"] == "/sources"
    assert src["summary"] == "BBC"


@pytest.mark.asyncio
async def test_activity_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _Session(
        claims=[_claim(offset_min=i) for i in range(5)],
        sources=[_source(offset_min=i + 100) for i in range(5)],
        discussions=[],
    )
    monkeypatch.setattr(activity_route, "session_scope", _scope_factory(sess))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/activity?limit=3")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["events"]) == 3
    # All three should be the most recent (claims are newer than sources here).
    assert all(e["kind"] == "claim" for e in body["events"])


@pytest.mark.asyncio
async def test_activity_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _Session(claims=[], sources=[], discussions=[])
    monkeypatch.setattr(activity_route, "session_scope", _scope_factory(sess))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/activity")

    assert resp.status_code == 200
    assert resp.json() == {"events": []}
