from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from argus_api.deps import get_session
from argus_api.main import app
from argus_api.routes import discussions as discussions_route
from argus_api.temporal_client import TemporalUnavailableError
from argus_core.db.models import DiscussionRunModel
from argus_core.schemas import DiscussionStatus
from httpx import ASGITransport, AsyncClient


class _FakeSession:
    def __init__(self) -> None:
        self.rows_by_id: dict[UUID, DiscussionRunModel] = {}
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        if isinstance(obj, DiscussionRunModel):
            self.rows_by_id[obj.id] = obj

    async def flush(self) -> None:
        return None

    async def get(self, _model: Any, ident: UUID) -> Any:
        return self.rows_by_id.get(ident)

    async def execute(self, _stmt: Any) -> Any:
        result = MagicMock()
        result.scalar_one.return_value = 0
        result.scalars.return_value.all.return_value = []
        return result


@pytest.fixture
def fake_session() -> _FakeSession:
    return _FakeSession()


@pytest.fixture
def client_with_session(fake_session: _FakeSession):
    async def _override() -> AsyncIterator[Any]:
        yield fake_session

    app.dependency_overrides[get_session] = _override
    try:
        yield fake_session
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_post_discussions_temporal_mode(
    monkeypatch: pytest.MonkeyPatch,
    client_with_session: _FakeSession,
) -> None:
    fake_client = MagicMock()
    fake_client.start_workflow = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr(discussions_route, "get_client", AsyncMock(return_value=fake_client))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/discussions",
            json={"topic": "Topic X", "vertical": "finance"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["mode"] == "temporal"
    assert UUID(body["discussion_id"])
    fake_client.start_workflow.assert_awaited_once()
    args, kwargs = fake_client.start_workflow.call_args
    assert args[0] == "DiscussionWorkflow"
    payload = args[1]
    assert payload["topic"] == "Topic X"
    assert payload["vertical"] == "finance"
    assert payload["discussion_id"] == body["discussion_id"]
    assert kwargs["id"] == body["workflow_id"]
    assert kwargs["task_queue"]
    assert UUID(payload["discussion_id"]) in client_with_session.rows_by_id


@pytest.mark.asyncio
async def test_post_discussions_inline_fallback(
    monkeypatch: pytest.MonkeyPatch,
    client_with_session: _FakeSession,
) -> None:
    monkeypatch.setattr(
        discussions_route,
        "get_client",
        AsyncMock(side_effect=TemporalUnavailableError("nope")),
    )

    inline_calls: list[str] = []

    async def _capture_inline(discussion_id: str) -> None:
        inline_calls.append(discussion_id)

    monkeypatch.setattr(discussions_route, "_run_inline", _capture_inline)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/discussions",
            json={"topic": "Topic Y", "vertical": "climate"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["mode"] == "inline"
    discussion_id = UUID(body["discussion_id"])
    assert discussion_id in client_with_session.rows_by_id
    row = client_with_session.rows_by_id[discussion_id]
    assert row.topic == "Topic Y"
    assert row.vertical == "climate"
    assert row.status == DiscussionStatus.PLANNING.value
    # BackgroundTasks runs the task after the response is returned.
    assert inline_calls == [body["discussion_id"]]
