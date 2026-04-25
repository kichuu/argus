"""Tests for the /discussions routes.

We avoid hitting Postgres by overriding ``get_session`` with a fake async
session that captures rows in an in-memory store, and by overriding
``get_launcher`` so the launcher.start coroutine returns a known id without
touching Temporal or running activities.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from argus_api.deps import get_session
from argus_api.main import app
from argus_api.routes.discussions import _row_to_summary  # noqa: F401  (sanity)
from argus_api.temporal_client import DiscussionLauncher, get_launcher
from argus_core.db.models import DiscussionRunModel
from httpx import ASGITransport, AsyncClient


class _FakeSession:
    """Minimal AsyncSession stand-in.

    Implements just enough of the SQLAlchemy AsyncSession surface that
    ``routes/discussions.py`` exercises in tests: ``add``, ``flush``, ``get``,
    ``execute(...).scalars().all()``.
    """

    def __init__(self, store: dict[type, dict[Any, Any]]) -> None:
        self.store = store

    def add(self, row: Any) -> None:
        bucket = self.store.setdefault(type(row), {})
        bucket[row.id] = row

    async def flush(self) -> None:  # no-op: in-memory adds are immediate
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def get(self, model: type, key: Any) -> Any:
        return self.store.get(model, {}).get(key)

    async def execute(self, _stmt: Any) -> Any:
        # The discussions routes only call execute() for list/messages/claims.
        # Tests here don't depend on those queries returning anything.
        class _Result:
            def scalars(self):
                class _Scalars:
                    def all(self_inner):  # noqa: N805
                        return []

                return _Scalars()

            def scalar_one(self):
                return 0

        return _Result()


@pytest.fixture
def fake_store() -> dict[type, dict[Any, Any]]:
    return {}


@pytest.fixture
def client(fake_store: dict[type, dict[Any, Any]]):
    async def _override_session():
        yield _FakeSession(fake_store)

    class _StubLauncher(DiscussionLauncher):
        async def start(self, topic: str, vertical: str, discussion_id: str) -> str:  # type: ignore[override]
            return discussion_id

    def _override_launcher() -> DiscussionLauncher:
        return _StubLauncher()

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_launcher] = _override_launcher
    try:
        yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_launcher, None)


@pytest.mark.asyncio
async def test_post_discussion_creates_row(
    client: AsyncClient,
    fake_store: dict[type, dict[Any, Any]],
) -> None:
    async with client as c:
        resp = await c.post("/discussions", json={"topic": "test"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "id" in body
    new_id = UUID(body["id"])
    assert body["status"] == "planning"

    # Row was persisted via session.add()
    assert DiscussionRunModel in fake_store
    assert new_id in fake_store[DiscussionRunModel]
    saved = fake_store[DiscussionRunModel][new_id]
    assert saved.topic == "test"
    assert saved.vertical == "geopolitics"  # default vertical
    assert saved.status == "planning"


@pytest.mark.asyncio
async def test_post_discussion_with_explicit_vertical(
    client: AsyncClient,
    fake_store: dict[type, dict[Any, Any]],
) -> None:
    async with client as c:
        resp = await c.post(
            "/discussions",
            json={"topic": "trade flows", "vertical": "finance"},
        )
    assert resp.status_code == 200
    new_id = UUID(resp.json()["id"])
    assert fake_store[DiscussionRunModel][new_id].vertical == "finance"


@pytest.mark.asyncio
async def test_discussions_route_params(
    client: AsyncClient,
    fake_store: dict[type, dict[Any, Any]],
) -> None:
    """POST accepts the new depth / source_kinds / auto_personas fields."""
    async with client as c:
        resp = await c.post(
            "/discussions",
            json={
                "topic": "x",
                "depth": "deep",
                "source_kinds": ["rss"],
                "auto_personas": False,
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "planning"
    new_id = UUID(body["id"])
    saved = fake_store[DiscussionRunModel][new_id]
    assert saved.topic == "x"
    assert saved.vertical == "geopolitics"


@pytest.mark.asyncio
async def test_get_discussion_404(client: AsyncClient) -> None:
    missing = uuid4()
    async with client as c:
        resp = await c.get(f"/discussions/{missing}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "discussion not found"


@pytest.mark.asyncio
async def test_get_messages_404_for_unknown_discussion(client: AsyncClient) -> None:
    missing = uuid4()
    async with client as c:
        resp = await c.get(f"/discussions/{missing}/messages")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_claims_404_for_unknown_discussion(client: AsyncClient) -> None:
    missing = uuid4()
    async with client as c:
        resp = await c.get(f"/discussions/{missing}/claims")
    assert resp.status_code == 404
