from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from dateutil import parser as date_parser

from argus_core.logging import get_logger
from argus_core.schemas import Source
from argus_core.settings import get_settings
from argus_core.trust import load_trust_config
from argus_ingestion.base import (
    SourceConnector,
    compute_content_hash,
    normalize_text,
)

logger = get_logger(__name__)


class GDELTConnector(SourceConnector):
    def __init__(
        self,
        query: str,
        time_window: tuple[datetime, datetime] | None = None,
        max_records: int = 250,
        timeout: float = 30.0,
    ) -> None:
        self.query = query
        self.time_window = time_window
        self.max_records = max_records
        self.timeout = timeout
        self._settings = get_settings()
        self._trust_config = load_trust_config()

    async def fetch(self) -> AsyncIterator[Source]:
        params = self._build_params()
        url = f"{self._settings.gdelt_base.rstrip('/')}/doc/doc"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()

        for article in payload.get("articles", []) or []:
            source = self._article_to_source(article)
            if source is not None:
                yield source

    def _build_params(self) -> dict[str, str]:
        params: dict[str, str] = {
            "query": self.query,
            "format": "json",
            "mode": "ArtList",
            "maxrecords": str(self.max_records),
        }
        if self.time_window is not None:
            start, end = self.time_window
            params["startdatetime"] = start.strftime("%Y%m%d%H%M%S")
            params["enddatetime"] = end.strftime("%Y%m%d%H%M%S")
        return params

    def _article_to_source(self, article: dict[str, Any]) -> Source | None:
        link: str | None = article.get("url")
        title: str = (article.get("title") or "").strip() or "(untitled)"
        seendate = article.get("seendate")
        domain = article.get("domain") or (urlparse(link).hostname if link else None)
        body = article.get("excerpt") or article.get("title") or ""
        raw_text = normalize_text(body)
        if not raw_text:
            logger.debug("gdelt_article_empty", url=link)
            return None

        published_at = self._parse_seendate(seendate)
        trust_tier = self._trust_config.tier_for_domain(domain) if domain else 4

        return Source(
            url=link,  # type: ignore[arg-type]
            title=title,
            content_hash=compute_content_hash(raw_text),
            raw_text=raw_text,
            fetched_at=datetime.now(timezone.utc),
            published_at=published_at,
            trust_tier=trust_tier,
            publisher=domain,
            language=article.get("language"),
        )

    @staticmethod
    def _parse_seendate(seendate: str | None) -> datetime | None:
        if not seendate:
            return None
        try:
            dt = date_parser.parse(seendate)
        except (ValueError, TypeError):
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
