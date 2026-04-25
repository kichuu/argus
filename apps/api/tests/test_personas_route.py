"""Tests for /personas and /entities/{id}/relations.

Mocks `session_scope` (imported into the route modules) to yield a fake
AsyncSession with canned objects. No real DB.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from argus_api.main import app
from argus_api.routes import entities as entities_route
from argus_api.routes import personas as personas_route
from httpx import ASGITransport, AsyncClient


class FakeResult:
    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(
        self,
        items: list | None = None,
        get_map: dict | None = None,
    ) -> None:
        self._items = items or []
        self._get_map = get_map or {}
        self.added: list = []
        self.deleted: list = []

    async def execute(self, stmt):
        return FakeResult(self._items)

    async def get(self, model, key):
        return self._get_map.get((model, key))

    def add(self, obj) -> None:
        self.added.append(obj)
        # Make POST /personas readable after flush.
        if not getattr(obj, "id", None):
            obj.id = uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(UTC)

    async def flush(self) -> None:
        return None

    async def refresh(self, obj) -> None:
        return None

    async def delete(self, obj) -> None:
        self.deleted.append(obj)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _make_session_scope(session: FakeSession):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


def _make_persona_row(**overrides):
    base = {
        "id": uuid4(),
        "frame": "skeptical regulator",
        "description": "challenges agency claims",
        "knowledge_emphasis": ["compliance", "risk"],
        "temperature": 0.7,
        "redlines": [],
        "bias": None,
        "model_assignment": None,
        "color": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_entity_row(**overrides):
    base = {
        "id": uuid4(),
        "canonical_name": "Subject",
        "entity_type": "person",
        "wikidata_id": None,
        "aliases": [],
        "description": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_relation_row(subject_id, object_id, **overrides):
    base = {
        "id": uuid4(),
        "subject_id": subject_id,
        "relation_type": "knows",
        "object_id": object_id,
        "evidence": [],
        "confidence": 0.8,
        "valid_from": None,
        "valid_to": None,
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------- /personas tests ----------


@pytest.mark.asyncio
async def test_list_personas_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(items=[])
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/personas")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_personas_returns_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _make_persona_row()
    session = FakeSession(items=[row])
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/personas")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["frame"] == "skeptical regulator"
    assert body[0]["knowledge_emphasis"] == ["compliance", "risk"]


@pytest.mark.asyncio
async def test_list_personas_frame_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    row = _make_persona_row(frame="trade analyst")
    session = FakeSession(items=[row])

    captured: dict = {}

    async def _execute(stmt):
        captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return FakeResult([row])

    session.execute = _execute  # type: ignore[assignment]
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/personas?frame=trade")

    assert resp.status_code == 200
    assert "trade" in captured["sql"].lower()


@pytest.mark.asyncio
async def test_get_persona_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/personas/{uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_persona_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import PersonaModel

    row = _make_persona_row()
    session = FakeSession(get_map={(PersonaModel, row.id): row})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/personas/{row.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(row.id)
    assert body["frame"] == row.frame


@pytest.mark.asyncio
async def test_create_persona(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/personas",
            json={
                "frame": "regional macro",
                "description": "asia-pacific FX flows",
                "knowledge_emphasis": ["fx", "trade"],
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["frame"] == "regional macro"
    assert body["knowledge_emphasis"] == ["fx", "trade"]
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_delete_persona_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/personas/{uuid4()}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_persona_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import PersonaModel

    row = _make_persona_row()
    session = FakeSession(get_map={(PersonaModel, row.id): row})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/personas/{row.id}")

    assert resp.status_code == 204
    assert session.deleted == [row]


@pytest.mark.asyncio
async def test_patch_persona_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/personas/{uuid4()}",
            json={"temperature": 0.42},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_persona_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import PersonaModel

    row = _make_persona_row()
    session = FakeSession(get_map={(PersonaModel, row.id): row})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/personas/{row.id}",
            json={
                "temperature": 0.42,
                "redlines": ["no impersonation"],
                "bias": "cautious",
                "model_assignment": "openai:gpt-4o-mini",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["temperature"] == 0.42
    assert body["redlines"] == ["no impersonation"]
    assert body["bias"] == "cautious"
    assert body["model_assignment"] == "openai:gpt-4o-mini"
    # Other fields untouched.
    assert body["frame"] == row.frame
    assert body["knowledge_emphasis"] == list(row.knowledge_emphasis)


@pytest.mark.asyncio
async def test_patch_persona_color_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import PersonaModel

    row = _make_persona_row()
    session = FakeSession(get_map={(PersonaModel, row.id): row})
    monkeypatch.setattr(personas_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/personas/{row.id}",
            json={"color": "var(--p-3)"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["color"] == "var(--p-3)"
    # Other fields untouched.
    assert body["frame"] == row.frame
    assert body["temperature"] == row.temperature


# ---------- /entities/{id}/relations tests ----------


@pytest.mark.asyncio
async def test_entity_relations_404(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(get_map={})
    monkeypatch.setattr(entities_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/entities/{uuid4()}/relations")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_entity_relations_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from argus_core.db.models import EntityModel

    subj = _make_entity_row()
    obj = _make_entity_row(canonical_name="Object")
    rel1 = _make_relation_row(subject_id=subj.id, object_id=obj.id, relation_type="knows")
    rel2 = _make_relation_row(
        subject_id=obj.id,
        object_id=subj.id,
        relation_type="employed_by",
        confidence=0.92,
    )

    captured: dict = {}

    async def _execute(stmt):
        captured["sql"] = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return FakeResult([rel1, rel2])

    session = FakeSession(get_map={(EntityModel, subj.id): subj})
    session.execute = _execute  # type: ignore[assignment]
    monkeypatch.setattr(entities_route, "session_scope", _make_session_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/entities/{subj.id}/relations")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    rel_types = {r["relation_type"] for r in body}
    assert rel_types == {"knows", "employed_by"}
    # Both subject_id and object_id presence in the WHERE clause.
    sql = captured["sql"].lower()
    assert "subject_id" in sql
    assert "object_id" in sql
