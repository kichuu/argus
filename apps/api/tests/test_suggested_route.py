"""Tests for /suggested-topics.

Mocks `session_scope` (and the OpenAI provider, when claims exist) so the
test never needs a real database or API key.
"""

from contextlib import asynccontextmanager

import pytest
from argus_api.main import app
from argus_api.routes import suggested as suggested_route
from httpx import ASGITransport, AsyncClient


class FakeResult:
    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, items: list | None = None) -> None:
        self._items = items or []

    async def execute(self, stmt):
        return FakeResult(self._items)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _make_session_scope(session: FakeSession):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


@pytest.mark.asyncio
async def test_suggested_topics_empty_when_no_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suggested_route._reset_cache()
    session = FakeSession(items=[])
    monkeypatch.setattr(
        suggested_route, "session_scope", _make_session_scope(session)
    )

    # Make sure the LLM is never called when there are no claims.
    def _no_provider(name: str):  # pragma: no cover - defensive
        raise AssertionError("provider should not be invoked when there are no claims")

    monkeypatch.setattr(suggested_route, "get_provider", _no_provider)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/suggested-topics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["topics"] == []
    assert body["claim_basis_count"] == 0
    assert "generated_at" in body
