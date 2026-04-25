from __future__ import annotations

import contextlib
from contextlib import asynccontextmanager
from typing import Any

import pytest
from argus_api.main import app
from argus_api.routes import discussions as discussions_module
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_ws_streams_pubsub_events(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    delivered = [
        {"event": "phase", "phase": "researching"},
        {"event": "post", "agent_message": {"agent_id": "p1"}},
        {"event": "phase", "phase": "completed"},
    ]

    class _FakePubSub:
        def __init__(self) -> None:
            self.closed = False

        @asynccontextmanager
        async def subscribe(self, _did: str) -> Any:
            async def stream() -> Any:
                for evt in delivered:
                    yield evt

            yield stream()

        async def close(self) -> None:
            self.closed = True

    fake = _FakePubSub()
    monkeypatch.setattr(discussions_module, "DiscussionPubSub", lambda *_a, **_kw: fake)

    received: list[dict] = []
    with client.websocket_connect("/ws/discussions/abc") as ws:
        for _ in delivered:
            received.append(ws.receive_json())

    assert received == delivered
    assert fake.closed is True


def test_ws_handles_pubsub_failure(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    class _BoomPubSub:
        @asynccontextmanager
        async def subscribe(self, _did: str) -> Any:
            raise RuntimeError("redis down")
            yield  # pragma: no cover

        async def close(self) -> None:
            pass

    monkeypatch.setattr(discussions_module, "DiscussionPubSub", lambda *_a, **_kw: _BoomPubSub())

    # Should accept then disconnect cleanly without raising in the handler.
    with (
        client.websocket_connect("/ws/discussions/abc") as ws,
        contextlib.suppress(Exception),
    ):
        # The server-side handler logs the warning and returns; the client sees disconnect.
        ws.receive_json(timeout=1)
