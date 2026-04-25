from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

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


class _ListSession:
    """Fake session that distinguishes count vs. row-select on execute().

    Mirrors enough of AsyncSession to drive ``list_discussions`` without a real DB.
    The route issues two ``execute`` calls per request: a ``func.count()`` query and
    a row-select ordered by ``started_at desc`` with limit/offset. We sniff the
    compiled SQL to decide which result to hand back.
    """

    def __init__(self, rows: list[DiscussionRunModel]) -> None:
        self.rows = rows
        self.calls: list[str] = []

    def add(self, _obj: Any) -> None:  # pragma: no cover - unused on list path
        return None

    async def flush(self) -> None:  # pragma: no cover - unused on list path
        return None

    async def get(self, _model: Any, _ident: UUID) -> Any:  # pragma: no cover
        return None

    async def execute(self, stmt: Any) -> Any:
        from sqlalchemy.dialects import postgresql

        compiled = str(
            stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        )
        self.calls.append(compiled)

        # Apply WHERE filters by parsing the compiled SQL for the values we set.
        filtered = list(self.rows)
        lowered = compiled.lower()
        if "discussion_runs.status" in lowered:
            for value in (
                DiscussionStatus.PLANNING.value,
                DiscussionStatus.RESEARCHING.value,
                DiscussionStatus.DEBATING.value,
                DiscussionStatus.SYNTHESIZING.value,
                DiscussionStatus.COMPLETED.value,
                DiscussionStatus.FAILED.value,
            ):
                if f"'{value}'" in compiled:
                    filtered = [r for r in filtered if r.status == value]
                    break
        if "discussion_runs.vertical" in lowered:
            for vertical in ("finance", "climate", "civic", "geopolitics", "general"):
                if f"'{vertical}'" in compiled:
                    filtered = [r for r in filtered if r.vertical == vertical]
                    break

        result = MagicMock()
        if "count(" in lowered:
            result.scalar_one.return_value = len(filtered)
            return result

        # Row-select: honor newest-first order plus LIMIT/OFFSET.
        ordered = sorted(filtered, key=lambda r: r.started_at, reverse=True)
        limit, offset = _extract_limit_offset(compiled)
        sliced = ordered[offset : offset + limit] if limit is not None else ordered[offset:]
        result.scalars.return_value.all.return_value = sliced
        return result


def _extract_limit_offset(sql: str) -> tuple[int | None, int]:
    import contextlib

    limit: int | None = None
    offset = 0
    tokens = sql.replace("\n", " ").split()
    for i, token in enumerate(tokens):
        upper = token.upper().rstrip(",")
        if upper == "LIMIT" and i + 1 < len(tokens):
            with contextlib.suppress(ValueError):
                limit = int(tokens[i + 1].rstrip(","))
        elif upper == "OFFSET" and i + 1 < len(tokens):
            with contextlib.suppress(ValueError):
                offset = int(tokens[i + 1].rstrip(","))
    return limit, offset


def _make_row(
    *,
    topic: str,
    vertical: str,
    status: DiscussionStatus,
    started_at: datetime,
    completed_at: datetime | None = None,
    final_claim_ids: list[str] | None = None,
) -> DiscussionRunModel:
    row = DiscussionRunModel(
        id=uuid4(),
        topic=topic,
        vertical=vertical,
        status=status.value,
        persona_ids=[],
        evidence_pack=[],
        final_claim_ids=final_claim_ids or [],
        started_at=started_at,
        completed_at=completed_at,
        error=None,
    )
    return row


def _override_session(session: Any) -> None:
    async def _override() -> AsyncIterator[Any]:
        yield session

    app.dependency_overrides[get_session] = _override


@pytest.mark.asyncio
async def test_list_discussions_returns_newest_first() -> None:
    base = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    rows = [
        _make_row(
            topic="oldest",
            vertical="finance",
            status=DiscussionStatus.COMPLETED,
            started_at=base,
            completed_at=base + timedelta(minutes=5),
            final_claim_ids=["c1", "c2"],
        ),
        _make_row(
            topic="middle",
            vertical="climate",
            status=DiscussionStatus.DEBATING,
            started_at=base + timedelta(hours=1),
        ),
        _make_row(
            topic="newest",
            vertical="finance",
            status=DiscussionStatus.PLANNING,
            started_at=base + timedelta(hours=2),
        ),
    ]
    session = _ListSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/discussions")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["limit"] == 50
    assert body["offset"] == 0
    topics = [item["topic"] for item in body["items"]]
    assert topics == ["newest", "middle", "oldest"]
    oldest_item = body["items"][2]
    assert oldest_item["final_claim_count"] == 2
    assert oldest_item["completed_at"] is not None
    assert body["items"][0]["completed_at"] is None


@pytest.mark.asyncio
async def test_list_discussions_pagination_respects_limit_and_offset() -> None:
    base = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    rows = [
        _make_row(
            topic=f"topic-{i}",
            vertical="finance",
            status=DiscussionStatus.PLANNING,
            started_at=base + timedelta(hours=i),
        )
        for i in range(5)
    ]
    session = _ListSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/discussions", params={"limit": 2, "offset": 1})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 1
    topics = [item["topic"] for item in body["items"]]
    # Newest-first is topic-4..topic-0; offset=1 limit=2 -> topic-3, topic-2.
    assert topics == ["topic-3", "topic-2"]


@pytest.mark.asyncio
async def test_list_discussions_status_filter() -> None:
    base = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    rows = [
        _make_row(
            topic="planned",
            vertical="finance",
            status=DiscussionStatus.PLANNING,
            started_at=base,
        ),
        _make_row(
            topic="done",
            vertical="finance",
            status=DiscussionStatus.COMPLETED,
            started_at=base + timedelta(hours=1),
        ),
        _make_row(
            topic="failed",
            vertical="climate",
            status=DiscussionStatus.FAILED,
            started_at=base + timedelta(hours=2),
        ),
    ]
    session = _ListSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/discussions",
                params={"status": DiscussionStatus.COMPLETED.value},
            )
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    topics = [item["topic"] for item in body["items"]]
    assert topics == ["done"]


@pytest.mark.asyncio
async def test_list_discussions_vertical_filter() -> None:
    base = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    rows = [
        _make_row(
            topic="fin-a",
            vertical="finance",
            status=DiscussionStatus.PLANNING,
            started_at=base,
        ),
        _make_row(
            topic="cli-a",
            vertical="climate",
            status=DiscussionStatus.PLANNING,
            started_at=base + timedelta(hours=1),
        ),
        _make_row(
            topic="fin-b",
            vertical="finance",
            status=DiscussionStatus.PLANNING,
            started_at=base + timedelta(hours=2),
        ),
    ]
    session = _ListSession(rows)
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/discussions", params={"vertical": "finance"})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    topics = [item["topic"] for item in body["items"]]
    assert topics == ["fin-b", "fin-a"]


@pytest.mark.asyncio
async def test_list_discussions_empty_result() -> None:
    session = _ListSession([])
    _override_session(session)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/discussions", params={"limit": 25, "offset": 10})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "limit": 25, "offset": 10}
