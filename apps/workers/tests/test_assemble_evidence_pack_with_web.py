from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


def _install_fake_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    rows: dict[Any, Any],
) -> dict[str, Any]:
    """Install a fake session_scope mirroring the existing test helper.

    `rows` maps ids to row instances. session.execute() returns a result whose
    .scalar_one_or_none() / .scalars().all() / .first() are all empty, which
    is the right behaviour when no SourceModel exists yet for the web URL.
    """
    from argus_workers.activities import discussion as discussion_mod

    captured: dict[str, Any] = {"sessions": [], "added": []}

    async def fake_get(_model: Any, key: Any) -> Any:
        return rows.get(key)

    async def fake_execute(*_args: Any, **_kwargs: Any) -> Any:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.first.return_value = None
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        return result

    @asynccontextmanager
    async def fake_session_scope():
        session = MagicMock()
        session.get = AsyncMock(side_effect=fake_get)
        session.execute = AsyncMock(side_effect=fake_execute)

        def _add(obj: Any) -> None:
            captured["added"].append(obj)

        session.add = MagicMock(side_effect=_add)
        captured["sessions"].append(session)
        yield session

    monkeypatch.setattr(discussion_mod, "session_scope", fake_session_scope)
    return captured


def _web_result(url: str, title: str, snippet: str):
    from argus_extraction.web_search import WebSearchResult

    text = f"{title}. {snippet}"
    return WebSearchResult(
        url=url,
        title=title,
        snippet=snippet,
        text=text,
        fetched_at=datetime.now(UTC),
    )


def _force_web_search_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the cached settings instance look like web search is on."""
    from argus_core.settings import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "web_search_enabled", True, raising=False)
    monkeypatch.setattr(s, "web_search_max_results", 5, raising=False)


@pytest.mark.asyncio
async def test_assemble_evidence_pack_uses_web_when_hybrid_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import discussion as discussion_mod

    _force_web_search_settings(monkeypatch)

    did = uuid4()
    row = MagicMock()
    row.topic = "battery storage costs"
    row.vertical = "climate"
    row.evidence_pack = None
    row.status = None

    captured = _install_fake_session_scope(monkeypatch, rows={did: row})

    fake_search = AsyncMock(
        return_value=[
            _web_result(
                "https://reuters.com/a",
                "Reuters on Storage",
                "Battery storage costs fell 12% year over year.",
            ),
            _web_result(
                "https://bloomberg.com/b",
                "Bloomberg on Storage",
                "Grid-scale battery deployments rose sharply in Q1.",
            ),
        ]
    )

    class _FakeWebSearchClient:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def search(self, query: str, max_results: int = 5):
            return await fake_search(query, max_results=max_results)

    monkeypatch.setattr(discussion_mod, "WebSearchClient", _FakeWebSearchClient)
    monkeypatch.setattr(
        discussion_mod, "_build_hybrid_retriever", AsyncMock(return_value=None)
    )

    async def boom_baseline(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("baseline should not be reached when web has results")

    monkeypatch.setattr(discussion_mod, "_baseline_evidence_pack", boom_baseline)

    result = await discussion_mod.assemble_evidence_pack(str(did))

    fake_search.assert_awaited_once()
    assert result["evidence_count"] == 2
    assert result["source"] == "web"

    # The persisted evidence pack should be EvidenceRef-shaped dicts.
    assert isinstance(row.evidence_pack, list)
    assert len(row.evidence_pack) == 2
    for entry in row.evidence_pack:
        assert "verbatim_span" in entry
        assert entry["char_end"] > entry["char_start"]
        assert entry["char_end"] - entry["char_start"] == len(entry["verbatim_span"])

    # Two SourceModel rows should have been added (the fake session.execute
    # always reports "no existing row" so both new sources persist).
    from argus_core.db.models import SourceModel

    added_sources = [a for a in captured["added"] if isinstance(a, SourceModel)]
    assert len(added_sources) == 2
    urls = {s.url for s in added_sources}
    assert "https://reuters.com/a" in urls
    assert "https://bloomberg.com/b" in urls


@pytest.mark.asyncio
async def test_assemble_evidence_pack_combines_web_and_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_retrieval.types import RetrievedSpan
    from argus_workers.activities import discussion as discussion_mod

    _force_web_search_settings(monkeypatch)

    did = uuid4()
    row = MagicMock()
    row.topic = "solar tariffs"
    row.vertical = "climate"
    row.evidence_pack = None
    row.status = None

    _install_fake_session_scope(monkeypatch, rows={did: row})

    fake_search = AsyncMock(
        return_value=[
            _web_result(
                "https://reuters.com/x",
                "Reuters Solar",
                "Solar tariffs were lowered by 5% in March.",
            ),
            _web_result(
                "https://bloomberg.com/y",
                "Bloomberg Solar",
                "Manufacturers warn of supply tightness after policy shift.",
            ),
        ]
    )

    class _FakeWebSearchClient:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def search(self, query: str, max_results: int = 5):
            return await fake_search(query, max_results=max_results)

    monkeypatch.setattr(discussion_mod, "WebSearchClient", _FakeWebSearchClient)

    fetched = datetime.now(UTC)
    src1, src2, src3 = uuid4(), uuid4(), uuid4()
    spans = [
        RetrievedSpan(
            verbatim_span="Tariffs cut 5% in March.",
            char_start=0,
            char_end=len("Tariffs cut 5% in March."),
            source_id=src1,
            fetched_at=fetched,
            trust_tier=2,
            score=0.9,
            entity_ids=[],
        ),
        RetrievedSpan(
            verbatim_span="Module prices stabilized.",
            char_start=0,
            char_end=len("Module prices stabilized."),
            source_id=src2,
            fetched_at=fetched,
            trust_tier=3,
            score=0.7,
            entity_ids=[],
        ),
        RetrievedSpan(
            verbatim_span="Supply chains tightened.",
            char_start=0,
            char_end=len("Supply chains tightened."),
            source_id=src3,
            fetched_at=fetched,
            trust_tier=1,
            score=0.6,
            entity_ids=[],
        ),
    ]

    fake_retriever = MagicMock()
    fake_retriever.retrieve = AsyncMock(return_value=spans)
    monkeypatch.setattr(
        discussion_mod,
        "_build_hybrid_retriever",
        AsyncMock(return_value=fake_retriever),
    )

    async def boom_baseline(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise AssertionError("baseline should not be reached")

    monkeypatch.setattr(discussion_mod, "_baseline_evidence_pack", boom_baseline)

    result = await discussion_mod.assemble_evidence_pack(str(did))

    assert result["evidence_count"] == 5
    assert result["source"] == "hybrid+web"

    # Web evidence should come first (fresher).
    assert isinstance(row.evidence_pack, list)
    assert len(row.evidence_pack) == 5
    hybrid_source_ids = {str(src1), str(src2), str(src3)}
    # The last 3 entries are the hybrid spans, in retriever order.
    tail_ids = [e["source_id"] for e in row.evidence_pack[-3:]]
    assert tail_ids == [str(src1), str(src2), str(src3)]
    # The first 2 entries are NOT hybrid source ids (they're new web sources).
    head_ids = [e["source_id"] for e in row.evidence_pack[:2]]
    for hid in head_ids:
        assert hid not in hybrid_source_ids


@pytest.mark.asyncio
async def test_assemble_evidence_pack_skips_web_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_core.settings import get_settings
    from argus_workers.activities import discussion as discussion_mod

    s = get_settings()
    monkeypatch.setattr(s, "web_search_enabled", False, raising=False)

    did = uuid4()
    row = MagicMock()
    row.topic = "topic"
    row.vertical = "geopolitics"
    row.evidence_pack = None
    row.status = None

    _install_fake_session_scope(monkeypatch, rows={did: row})

    sentinel = AsyncMock(side_effect=AssertionError("web search should not run"))

    class _FakeWebSearchClient:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def search(self, *_args: Any, **_kwargs: Any):
            await sentinel()

    monkeypatch.setattr(discussion_mod, "WebSearchClient", _FakeWebSearchClient)
    monkeypatch.setattr(
        discussion_mod, "_build_hybrid_retriever", AsyncMock(return_value=None)
    )

    async def fake_baseline(vertical: str, limit: int = 20) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(discussion_mod, "_baseline_evidence_pack", fake_baseline)

    result = await discussion_mod.assemble_evidence_pack(str(did))
    assert result["source"] == "baseline"
    sentinel.assert_not_awaited()
