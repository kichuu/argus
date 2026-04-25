"""Redis pub/sub for live discussion event streaming.

Publisher writes JSON-encoded events to channel `discussion:{id}`.
WebSocket subscribers consume them. Polling clients still hit the DB
(messages persist in parallel) so this is purely additive.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis_aio

from argus_core.settings import get_settings


def _channel(discussion_id: str) -> str:
    return f"discussion:{discussion_id}"


class DiscussionPubSub:
    """Thin wrapper around redis.asyncio for per-discussion pub/sub.

    Reuses one publisher connection per instance; subscribe() takes a
    fresh connection so a long-lived subscription doesn't tie up the
    publisher.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._url = redis_url or get_settings().redis_url
        self._pub: redis_aio.Redis | None = None

    async def _publisher(self) -> redis_aio.Redis:
        if self._pub is None:
            self._pub = redis_aio.from_url(self._url, decode_responses=True)
        return self._pub

    async def publish(self, discussion_id: str, event: dict) -> int:
        client = await self._publisher()
        return await client.publish(_channel(discussion_id), json.dumps(event, default=str))

    @asynccontextmanager
    async def subscribe(self, discussion_id: str) -> AsyncIterator[AsyncIterator[dict]]:
        client = redis_aio.from_url(self._url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(_channel(discussion_id))

        async def stream() -> AsyncIterator[dict]:
            async for raw in pubsub.listen():
                if raw.get("type") != "message":
                    continue
                payload = raw.get("data")
                if not isinstance(payload, str):
                    continue
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    continue

        try:
            yield stream()
        finally:
            await pubsub.unsubscribe(_channel(discussion_id))
            await pubsub.close()
            await client.close()

    async def close(self) -> None:
        if self._pub is not None:
            await self._pub.close()
            self._pub = None
