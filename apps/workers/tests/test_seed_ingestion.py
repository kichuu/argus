"""Tests for the seed ingestion config and CLI loop."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlparse

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_CONFIG = REPO_ROOT / "config" / "seed_sources.yaml"


def _import_run_ingestion():
    import importlib.util
    import sys

    script_path = REPO_ROOT / "scripts" / "run_ingestion.py"
    spec = importlib.util.spec_from_file_location("run_ingestion", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_ingestion"] = module
    spec.loader.exec_module(module)
    return module


def test_seed_config_parses_and_validates() -> None:
    run_ingestion = _import_run_ingestion()
    config = run_ingestion.load_config(SEED_CONFIG)
    assert set(config.verticals.keys()) >= {
        "finance",
        "climate",
        "civic",
        "geopolitics",
        "general",
    }
    total = sum(len(feeds) for feeds in config.verticals.values())
    assert 23 <= total <= 35, f"expected 23-35 feeds, got {total}"
    for _vertical, specs in config.verticals.items():
        for spec in specs:
            assert spec.name
            assert 1 <= spec.trust_tier <= 2, "seed feeds should be tier-1/2 only"
            assert isinstance(spec.tags, list)


def test_seed_feed_urls_are_syntactically_valid() -> None:
    raw = yaml.safe_load(SEED_CONFIG.read_text(encoding="utf-8"))
    for vertical, specs in raw["verticals"].items():
        for spec in specs:
            url = spec["feed_url"]
            parsed = urlparse(url)
            assert parsed.scheme in {"http", "https"}, (vertical, spec["name"], url)
            assert parsed.netloc, (vertical, spec["name"], url)


def test_feeds_for_filters_by_vertical() -> None:
    run_ingestion = _import_run_ingestion()
    config = run_ingestion.load_config(SEED_CONFIG)
    fin = config.feeds_for("finance")
    assert fin
    assert all(v == "finance" for v, _ in fin)
    all_feeds = config.feeds_for(None)
    assert len(all_feeds) >= len(fin)


def test_feeds_for_unknown_vertical_raises() -> None:
    run_ingestion = _import_run_ingestion()
    config = run_ingestion.load_config(SEED_CONFIG)
    with pytest.raises(KeyError):
        config.feeds_for("does-not-exist")


def test_trust_overrides_uses_hostname() -> None:
    run_ingestion = _import_run_ingestion()
    out = run_ingestion._trust_overrides_for("https://example.com/path/feed.xml", 1)
    assert out == {"example.com": 1}


def test_build_span_uses_first_500_chars() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from argus_core.schemas import Source

    run_ingestion = _import_run_ingestion()
    src = Source(
        id=uuid4(),
        title="t",
        content_hash="a" * 64,
        raw_text="x" * 1000,
        fetched_at=datetime.now(UTC),
        trust_tier=1,
    )
    span = run_ingestion._build_span(src)
    assert span.char_start == 0
    assert span.char_end == 500
    assert span.verbatim_span == "x" * 500
    assert span.score == 1.0


def test_build_span_short_text() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from argus_core.schemas import Source

    run_ingestion = _import_run_ingestion()
    src = Source(
        id=uuid4(),
        title="t",
        content_hash="b" * 64,
        raw_text="hello world",
        fetched_at=datetime.now(UTC),
        trust_tier=2,
    )
    span = run_ingestion._build_span(src)
    assert span.char_end == len("hello world")
    assert span.verbatim_span == "hello world"


def _make_source(content_hash: str, text: str = "Some article body."):
    from datetime import UTC, datetime

    from argus_core.schemas import Source

    return Source(
        url="https://example.com/a",
        feed_url="https://example.com/feed",
        title=f"title-{content_hash[:6]}",
        content_hash=content_hash,
        raw_text=text,
        fetched_at=datetime.now(UTC),
        trust_tier=1,
        publisher="example.com",
    )


class _FakeRSSConnector:
    """Stand-in for RSSConnector that yields preset Sources."""

    sources: ClassVar[list] = []

    def __init__(self, feed_urls, trust_tier_overrides=None) -> None:
        self.feed_urls = feed_urls
        self.trust_tier_overrides = trust_tier_overrides or {}

    async def fetch(self):
        for s in type(self).sources:
            yield s


class _FakeSession:
    def __init__(self, existing_hashes: set[str]) -> None:
        self.existing_hashes = existing_hashes
        self.added: list = []

    async def execute(self, stmt):
        # parse the where clause: only used for content_hash existence here.
        # We inspect the compiled SQL parameters via the stmt's whereclause.
        target = _hash_from_stmt(stmt)
        present = target in self.existing_hashes
        return SimpleNamespace(first=lambda: ("x",) if present else None)

    def add(self, obj) -> None:
        self.added.append(obj)


def _hash_from_stmt(stmt) -> str:
    # The select uses .where(SourceModel.content_hash == content_hash);
    # compile with literal binds so we can read the value back.
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    # Extract the literal between single quotes after content_hash =
    import re

    m = re.search(r"content_hash\s*=\s*'([^']+)'", sql)
    if not m:
        return ""
    return m.group(1)


@pytest.mark.asyncio
async def test_main_loop_persists_each_entry(monkeypatch) -> None:
    run_ingestion = _import_run_ingestion()

    sources = [
        _make_source("a" * 64, text="article one body"),
        _make_source("b" * 64, text="article two body"),
        _make_source("c" * 64, text="article three body"),
    ]
    _FakeRSSConnector.sources = sources

    fake_session = _FakeSession(existing_hashes=set())

    @asynccontextmanager
    async def fake_session_scope():
        yield fake_session

    monkeypatch.setattr(run_ingestion, "RSSConnector", _FakeRSSConnector)
    monkeypatch.setattr(run_ingestion, "session_scope", fake_session_scope)

    from argus_core.db.models import SourceModel

    spec = run_ingestion.FeedSpec(
        name="t",
        feed_url="https://example.com/feed",
        trust_tier=1,
        tags=[],
    )
    stats = run_ingestion.IngestionStats()

    embedder = MagicMock()
    embedder.embed_one = AsyncMock(return_value=[0.0] * 8)
    vector_index = MagicMock()
    vector_index.upsert_span = AsyncMock(return_value=None)

    await run_ingestion._process_feed(
        "general",
        spec,
        max_per_feed=10,
        dry_run=False,
        embed=True,
        embedder=embedder,
        vector_index=vector_index,
        stats=stats,
    )

    assert stats.feeds_processed == 1
    assert stats.sources_stored == 3
    assert stats.sources_skipped == 0
    assert stats.errors == 0
    assert stats.embeddings_upserted == 3
    assert len(fake_session.added) == 3
    assert all(isinstance(o, SourceModel) for o in fake_session.added)
    assert embedder.embed_one.await_count == 3
    assert vector_index.upsert_span.await_count == 3


@pytest.mark.asyncio
async def test_main_loop_skips_duplicate_content_hash(monkeypatch) -> None:
    run_ingestion = _import_run_ingestion()

    dup_hash = "d" * 64
    new_hash = "e" * 64
    _FakeRSSConnector.sources = [
        _make_source(dup_hash, text="dup body"),
        _make_source(new_hash, text="new body"),
    ]

    fake_session = _FakeSession(existing_hashes={dup_hash})

    @asynccontextmanager
    async def fake_session_scope():
        yield fake_session

    monkeypatch.setattr(run_ingestion, "RSSConnector", _FakeRSSConnector)
    monkeypatch.setattr(run_ingestion, "session_scope", fake_session_scope)

    spec = run_ingestion.FeedSpec(
        name="t",
        feed_url="https://example.com/feed",
        trust_tier=1,
        tags=[],
    )
    stats = run_ingestion.IngestionStats()

    await run_ingestion._process_feed(
        "general",
        spec,
        max_per_feed=10,
        dry_run=False,
        embed=False,
        embedder=None,
        vector_index=None,
        stats=stats,
    )

    assert stats.sources_stored == 1
    assert stats.sources_skipped == 1
    assert stats.errors == 0
    assert stats.embeddings_upserted == 0
    assert len(fake_session.added) == 1


@pytest.mark.asyncio
async def test_main_loop_respects_max_per_feed(monkeypatch) -> None:
    run_ingestion = _import_run_ingestion()

    _FakeRSSConnector.sources = [
        _make_source(chr(ord("a") + i) * 64, text=f"body {i}") for i in range(5)
    ]

    fake_session = _FakeSession(existing_hashes=set())

    @asynccontextmanager
    async def fake_session_scope():
        yield fake_session

    monkeypatch.setattr(run_ingestion, "RSSConnector", _FakeRSSConnector)
    monkeypatch.setattr(run_ingestion, "session_scope", fake_session_scope)

    spec = run_ingestion.FeedSpec(
        name="t",
        feed_url="https://example.com/feed",
        trust_tier=1,
        tags=[],
    )
    stats = run_ingestion.IngestionStats()

    await run_ingestion._process_feed(
        "general",
        spec,
        max_per_feed=2,
        dry_run=False,
        embed=False,
        embedder=None,
        vector_index=None,
        stats=stats,
    )

    assert stats.sources_stored == 2
    assert len(fake_session.added) == 2


@pytest.mark.asyncio
async def test_dry_run_skips_db_writes(monkeypatch) -> None:
    run_ingestion = _import_run_ingestion()

    _FakeRSSConnector.sources = [_make_source("f" * 64, text="dry body")]
    fake_session = _FakeSession(existing_hashes=set())

    @asynccontextmanager
    async def fake_session_scope():
        yield fake_session

    monkeypatch.setattr(run_ingestion, "RSSConnector", _FakeRSSConnector)
    monkeypatch.setattr(run_ingestion, "session_scope", fake_session_scope)

    spec = run_ingestion.FeedSpec(
        name="t",
        feed_url="https://example.com/feed",
        trust_tier=1,
        tags=[],
    )
    stats = run_ingestion.IngestionStats()

    await run_ingestion._process_feed(
        "general",
        spec,
        max_per_feed=5,
        dry_run=True,
        embed=False,
        embedder=None,
        vector_index=None,
        stats=stats,
    )

    assert stats.sources_stored == 1
    assert fake_session.added == []
