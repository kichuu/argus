"""Tests for /health/system.

Mocks `session_scope` (imported into the health route module) plus the
qdrant client and GraphQuerier hooks, so we never reach external services.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from argus_api.main import app
from argus_api.routes import health as health_route
from httpx import ASGITransport, AsyncClient


# ---------- fakes ----------


class _ScalarOne:
    def __init__(self, v: Any) -> None:
        self._v = v

    def scalar_one(self) -> Any:
        return self._v


class _DBSession:
    """Returns canned scalar values keyed off SQL keywords."""

    def __init__(
        self,
        *,
        claims_total: int = 0,
        claims_24h: int = 0,
        sources_total: int = 0,
        sources_24h: int = 0,
        entities_total: int = 0,
        discussions_total: int = 0,
        discussions_running: int = 0,
        last_ingest_at: datetime | None = None,
    ) -> None:
        self._counts = {
            ("claims", False): claims_total,
            ("claims", True): claims_24h,
            ("sources", False): sources_total,
            ("sources", True): sources_24h,
            ("entities", False): entities_total,
            ("discussions_total", False): discussions_total,
            ("discussions_running", False): discussions_running,
        }
        self._last_ingest = last_ingest_at

    async def execute(self, stmt):
        try:
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()
        except Exception:
            sql = str(stmt).lower()

        if "max(" in sql:
            return _ScalarOne(self._last_ingest)

        if "count(" in sql:
            if "discussion_runs" in sql:
                if "planning" in sql or "researching" in sql or "debating" in sql:
                    return _ScalarOne(self._counts[("discussions_running", False)])
                return _ScalarOne(self._counts[("discussions_total", False)])
            if "claims" in sql:
                key = ("claims", "created_at" in sql and ">=" in sql)
                return _ScalarOne(self._counts[key])
            if "sources" in sql:
                key = ("sources", "fetched_at" in sql and ">=" in sql)
                return _ScalarOne(self._counts[key])
            if "entities" in sql:
                return _ScalarOne(self._counts[("entities", False)])
        return _ScalarOne(0)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _scope_factory(session: _DBSession):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


def _patch_db(monkeypatch: pytest.MonkeyPatch, session: _DBSession) -> None:
    monkeypatch.setattr(health_route, "session_scope", _scope_factory(session))


def _patch_scheduler(monkeypatch: pytest.MonkeyPatch, *, running: bool) -> None:
    class _Sched:
        def is_running(self) -> bool:
            return running

    monkeypatch.setattr(health_route, "get_scheduler", lambda: _Sched())


# ---------- tests ----------


@pytest.mark.asyncio
async def test_health_system_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _DBSession(
        claims_total=152,
        claims_24h=47,
        sources_total=89,
        sources_24h=31,
        entities_total=12,
        discussions_total=8,
        discussions_running=0,
        last_ingest_at=datetime(2026, 4, 25, 10, 38, tzinfo=UTC),
    )
    _patch_db(monkeypatch, sess)
    _patch_scheduler(monkeypatch, running=True)

    # Fake qdrant client returning a populated collection.
    class _FakeInfo:
        def __init__(self, points: int) -> None:
            self.points_count = points

    class _FakeQdrant:
        def __init__(self, **kwargs):  # noqa: ARG002
            pass

        async def get_collection(self, name: str):  # noqa: ARG002
            return _FakeInfo(42)

        async def close(self) -> None:
            return None

    import qdrant_client

    monkeypatch.setattr(qdrant_client, "AsyncQdrantClient", _FakeQdrant)

    async def _fake_age(self):  # noqa: ARG001
        return health_route.AgeStatus(graph="argus_graph", node_count=0, available=True)

    # Replace the AGE collector entirely to avoid hitting the DB.
    async def _collect_age_status():
        return health_route.AgeStatus(graph="argus_graph", node_count=0, available=True)

    monkeypatch.setattr(health_route, "_collect_age_status", _collect_age_status)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/system")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["api_version"]
    assert body["scheduler"] == {"running": True, "interval_seconds": pytest.approx(body["scheduler"]["interval_seconds"])}
    assert body["scheduler"]["running"] is True
    assert isinstance(body["scheduler"]["interval_seconds"], int)
    assert body["db"] == {
        "claims_total": 152,
        "claims_24h": 47,
        "sources_total": 89,
        "sources_24h": 31,
        "entities_total": 12,
        "discussions_total": 8,
        "discussions_running": 0,
    }
    assert body["qdrant"] == {
        "collection": "argus_evidence",
        "points_count": 42,
        "available": True,
    }
    assert body["age"] == {"graph": "argus_graph", "node_count": 0, "available": True}
    assert body["last_ingest_at"].startswith("2026-04-25T10:38")


@pytest.mark.asyncio
async def test_health_system_qdrant_down(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _DBSession()
    _patch_db(monkeypatch, sess)
    _patch_scheduler(monkeypatch, running=False)

    class _FailingQdrant:
        def __init__(self, **kwargs):  # noqa: ARG002
            pass

        async def get_collection(self, name: str):  # noqa: ARG002
            raise ConnectionError("qdrant unreachable")

        async def close(self) -> None:
            return None

    import qdrant_client

    monkeypatch.setattr(qdrant_client, "AsyncQdrantClient", _FailingQdrant)

    async def _collect_age_status():
        return health_route.AgeStatus(graph="argus_graph", node_count=None, available=False)

    monkeypatch.setattr(health_route, "_collect_age_status", _collect_age_status)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/system")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scheduler"]["running"] is False
    assert body["qdrant"]["available"] is False
    assert body["qdrant"]["points_count"] is None
    assert body["age"]["available"] is False
    assert body["age"]["node_count"] is None
    assert body["last_ingest_at"] is None
