import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import feedparser
from argus_core.logging import get_logger
from argus_core.schemas import Source
from argus_core.trust import load_trust_config
from dateutil import parser as date_parser

from argus_ingestion.base import (
    SourceConnector,
    compute_content_hash,
    normalize_text,
)

logger = get_logger(__name__)


class RSSConnector(SourceConnector):
    def __init__(
        self,
        feed_urls: list[str],
        trust_tier_overrides: dict[str, int] | None = None,
    ) -> None:
        self.feed_urls = feed_urls
        self.trust_tier_overrides = trust_tier_overrides or {}
        self._trust_config = load_trust_config()

    async def fetch(self) -> AsyncIterator[Source]:
        for feed_url in self.feed_urls:
            parsed = await asyncio.to_thread(feedparser.parse, feed_url)
            for entry in parsed.entries:
                source = self._entry_to_source(entry, feed_url)
                if source is not None:
                    yield source

    def _entry_to_source(self, entry: Any, feed_url: str) -> Source | None:
        link: str | None = entry.get("link")
        title: str = entry.get("title", "").strip() or "(untitled)"
        body = self._entry_body(entry)
        raw_text = normalize_text(body)
        if not raw_text:
            logger.debug("rss_entry_empty", feed_url=feed_url, title=title)
            return None

        published_at = self._entry_published(entry)
        host = urlparse(link).hostname if link else None
        trust_tier = self._resolve_trust_tier(host)

        return Source(
            url=link,  # type: ignore[arg-type]
            feed_url=feed_url,  # type: ignore[arg-type]
            title=title,
            content_hash=compute_content_hash(raw_text),
            raw_text=raw_text,
            fetched_at=datetime.now(UTC),
            published_at=published_at,
            trust_tier=trust_tier,
            publisher=host,
        )

    @staticmethod
    def _entry_body(entry: Any) -> str:
        contents = entry.get("content")
        if contents:
            for c in contents:
                value = c.get("value")
                if value:
                    return value
        return entry.get("summary") or entry.get("description") or ""

    @staticmethod
    def _entry_published(entry: Any) -> datetime | None:
        for key in ("published", "updated", "created"):
            raw = entry.get(key)
            if not raw:
                continue
            try:
                dt = date_parser.parse(raw)
            except (ValueError, TypeError):
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        return None

    def _resolve_trust_tier(self, host: str | None) -> int:
        if not host:
            return 4
        if host in self.trust_tier_overrides:
            return self.trust_tier_overrides[host]
        return self._trust_config.tier_for_domain(host)
