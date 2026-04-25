from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from argus_core import pubsub as pubsub_module
from argus_core.pubsub import DiscussionPubSub


@pytest.mark.asyncio
async def test_publish_encodes_json_on_correct_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = MagicMock()
    fake_client.publish = AsyncMock(return_value=1)

    monkeypatch.setattr(
        pubsub_module.redis_aio,
        "from_url",
        lambda *_, **__: fake_client,
    )

    ps = DiscussionPubSub("redis://test")
    delivered = await ps.publish("abc-123", {"event": "phase", "phase": "researching"})

    assert delivered == 1
    fake_client.publish.assert_awaited_once()
    channel, payload = fake_client.publish.await_args.args
    assert channel == "discussion:abc-123"
    decoded = json.loads(payload)
    assert decoded == {"event": "phase", "phase": "researching"}


@pytest.mark.asyncio
async def test_subscribe_yields_decoded_events_and_unsubscribes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delivered: list[dict[str, Any]] = [
        {"type": "subscribe"},  # ignored
        {"type": "message", "data": json.dumps({"event": "phase", "phase": "debating"})},
        {"type": "message", "data": json.dumps({"event": "post", "agent_id": "p1"})},
    ]

    async def listen() -> Any:
        for item in delivered:
            yield item

    fake_pubsub = MagicMock()
    fake_pubsub.subscribe = AsyncMock()
    fake_pubsub.unsubscribe = AsyncMock()
    fake_pubsub.close = AsyncMock()
    fake_pubsub.listen = listen

    fake_client = MagicMock()
    fake_client.pubsub = MagicMock(return_value=fake_pubsub)
    fake_client.close = AsyncMock()

    monkeypatch.setattr(
        pubsub_module.redis_aio,
        "from_url",
        lambda *_, **__: fake_client,
    )

    ps = DiscussionPubSub("redis://test")
    received: list[dict] = []
    async with ps.subscribe("xyz") as events:
        async for evt in events:
            received.append(evt)

    assert received == [
        {"event": "phase", "phase": "debating"},
        {"event": "post", "agent_id": "p1"},
    ]
    fake_pubsub.subscribe.assert_awaited_once_with("discussion:xyz")
    fake_pubsub.unsubscribe.assert_awaited_once_with("discussion:xyz")
    fake_pubsub.close.assert_awaited()
    fake_client.close.assert_awaited()
