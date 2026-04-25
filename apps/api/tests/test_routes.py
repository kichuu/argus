"""Route tests for /claims, /entities, /sources.

Mocks `session_scope` (imported into each route module) to yield a fake
AsyncSession that returns canned model objects. We intentionally avoid
spinning up a real DB.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from argus_api.main import app
from argus_api.routes import claims as claims_route
from argus_api.routes import entities as entities_route
from argus_api.routes import sources as sources_route
from httpx import ASGITransport, AsyncClient

# ---------- Fake session helpers ----------


class FakeResult:
    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class FakeSession:
    """Lightweight stand-in for AsyncSession.

    `execute(stmt)` ignores the statement and returns the canned `_items`.
    `get(model, id)` returns whatever is in `_get_map[(model, id)]`.
    """

    def __init__(
        self,
        items: list | None = None,
        get_map: dict | None = None,
    ) -> None:
        self._items = items or []
        self._get_map = get_map or {}

    async def execute(self, stmt):
        return FakeResult(self._items)

    async def get(self, model, key):
        return self._get_map.get((model, key))

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _make_session_scope(session: FakeSession):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


# ---------- Fixtures: fake DB rows ----------


def _make_source_row(**overrides):
    base = {
        "id": uuid4(),
        "url": "https://example.com/article",
        "feed_url": None,
        "title": "Example Source",
        "content_hash": "abc123",
        "raw_text": "hello world",
        "fetched_at": datetime.now(UTC),
        "published_at": None,
        "license": None,
        "trust_tier": 3,
        "publisher": "Example Publisher",
        "language": "en",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_entity_row(**overrides):
    base = {
        "id": uuid4(),
        "canonical_name": "Alice",
        "entity_type": "person",
        "wikidata_id": None,
        "aliases": [],
        "description": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_claim_row(**overrides):
    base = {
        "id": uuid4(),
        "statement": "The sky is blue.",
        "status": "likely_true",
        "confidence": 0.9,
        "supporting_evidence": [
            {
                "source_id": str(uuid4()),
                "verbatim_span": "the sky",
                "char_start": 0,
                "char_end": 7,
                "fetched_at": datetime.now(UTC).isoformat(),
                "trust_tier": 2,
            }
        ],
        "contradicting_evidence": [],
        "affected_entities": [],
        "agent_consensus": {"agree": 1, "disagree": 0, "uncertain": 0},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------- Tests ----------


@pytest.mark.asyncio
async def test_list_sources_returns_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    rss_row = _make_source_row(
        feed_url="https://example.com/feed.xml", title="Feed Source"
    )
    api_row = _make_source_row(url="https://api.example.com", feed_url=None)
    session = FakeSession(items=[rss_row, api_row])
    monkeypatch.setattr(sources_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/sources")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["type"] == "rss"
    assert body[1]["type"] == "api"
    assert all(item["status"] == "ok" for item in body)
    assert all("id" in item and "name" in item for item in body)


@pytest.mark.asyncio
async def test_list_sources_status_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _make_source_row()
    session = FakeSession(items=[row])
    monkeypatch.setattr(sources_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # "ok" matches our derived status, "down" should filter out everything.
        ok_resp = await client.get("/sources?status=ok")
        down_resp = await client.get("/sources?status=down")

    assert ok_resp.status_code == 200
    assert len(ok_resp.json()) == 1
    assert down_resp.status_code == 200
    assert down_resp.json() == []


@pytest.mark.asyncio
async def test_get_source_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(sources_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/sources/{uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_source_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import SourceModel

    row = _make_source_row(raw_text="x" * 42)
    session = FakeSession(get_map={(SourceModel, row.id): row})
    monkeypatch.setattr(sources_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/sources/{row.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["raw_text_length"] == 42
    assert "raw_text" not in body  # don't leak full text


@pytest.mark.asyncio
async def test_list_claims_filter_by_status(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _make_claim_row(status="likely_true")
    session = FakeSession(items=[row])

    captured: dict = {}

    async def _execute(stmt):
        # Capture the compiled SQL to assert the WHERE clause was applied.
        captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return FakeResult([row])

    session.execute = _execute  # type: ignore[assignment]
    monkeypatch.setattr(claims_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/claims?status=likely_true")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["text"] == "The sky is blue."
    assert body[0]["source_id"] is not None
    assert "likely_true" in captured["sql"]


@pytest.mark.asyncio
async def test_get_claim_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import ClaimModel

    row = _make_claim_row()
    session = FakeSession(get_map={(ClaimModel, row.id): row})
    monkeypatch.setattr(claims_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/claims/{row.id}/evidence")

    assert resp.status_code == 200
    evidence = resp.json()
    assert isinstance(evidence, list)
    assert len(evidence) == 1
    assert evidence[0]["verbatim_span"] == "the sky"


@pytest.mark.asyncio
async def test_get_claim_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(claims_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/claims/{uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_entities_filter_by_type(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _make_entity_row(entity_type="person", canonical_name="Bob")
    session = FakeSession(items=[row])

    captured: dict = {}

    async def _execute(stmt):
        captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return FakeResult([row])

    session.execute = _execute  # type: ignore[assignment]
    monkeypatch.setattr(entities_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/entities?type=person")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["type"] == "person"
    assert body[0]["canonical_name"] == "Bob"
    assert "person" in captured["sql"]


@pytest.mark.asyncio
async def test_list_entities_q_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _make_entity_row(canonical_name="Alice")
    session = FakeSession(items=[row])

    captured: dict = {}

    async def _execute(stmt):
        captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return FakeResult([row])

    session.execute = _execute  # type: ignore[assignment]
    monkeypatch.setattr(entities_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/entities?q=ali")

    assert resp.status_code == 200
    assert "ali" in captured["sql"].lower()


@pytest.mark.asyncio
async def test_get_entity_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(entities_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/entities/{uuid4()}")

    assert resp.status_code == 404


# Sanity-check unused MagicMock import isn't dead — used as a placeholder if needed.
_ = MagicMock
