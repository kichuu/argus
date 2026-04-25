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
    """Replace `session_scope` in the discussion activities module with a
    fake async context manager that returns a session-like MagicMock.

    `rows` maps row IDs (or any sentinel) to the row instance returned by
    `session.get(Model, key)`. The same rows are mutated in place across
    successive `session_scope()` blocks, mimicking persistence.
    """
    from argus_workers.activities import discussion as discussion_mod

    captured: dict[str, Any] = {"sessions": []}

    async def fake_get(_model: Any, key: Any) -> Any:
        return rows.get(key)

    async def fake_execute(*_args: Any, **_kwargs: Any) -> Any:
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        return result

    @asynccontextmanager
    async def fake_session_scope():
        session = MagicMock()
        session.get = AsyncMock(side_effect=fake_get)
        session.execute = AsyncMock(side_effect=fake_execute)
        session.add = MagicMock()
        captured["sessions"].append(session)
        yield session

    monkeypatch.setattr(discussion_mod, "session_scope", fake_session_scope)
    return captured


@pytest.mark.asyncio
async def test_assemble_evidence_pack_falls_back_to_baseline_when_retriever_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import discussion as discussion_mod

    did = uuid4()

    row = MagicMock()
    row.topic = "central bank balance sheets"
    row.vertical = "finance"
    row.evidence_pack = None
    row.status = None

    _install_fake_session_scope(monkeypatch, rows={did: row})

    monkeypatch.setattr(
        discussion_mod, "_build_hybrid_retriever", AsyncMock(return_value=None)
    )

    baseline_calls: dict[str, Any] = {"count": 0, "vertical": None}

    async def fake_baseline(vertical: str, limit: int = 20) -> list[dict[str, Any]]:
        baseline_calls["count"] += 1
        baseline_calls["vertical"] = vertical
        return [
            {
                "source_id": str(uuid4()),
                "verbatim_span": "fallback span",
                "char_start": 0,
                "char_end": len("fallback span"),
                "fetched_at": datetime.now(UTC).isoformat(),
                "trust_tier": 2,
            }
        ]

    monkeypatch.setattr(discussion_mod, "_baseline_evidence_pack", fake_baseline)

    result = await discussion_mod.assemble_evidence_pack(str(did))

    assert baseline_calls["count"] == 1
    assert baseline_calls["vertical"] == "finance"
    assert result["evidence_count"] == 1
    assert result["source"] == "baseline"
    assert isinstance(row.evidence_pack, list)
    assert len(row.evidence_pack) == 1
    assert row.evidence_pack[0]["verbatim_span"] == "fallback span"


@pytest.mark.asyncio
async def test_assemble_evidence_pack_persists_translated_hybrid_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_retrieval.types import RetrievedSpan
    from argus_workers.activities import discussion as discussion_mod

    did = uuid4()
    src1, src2, src3 = uuid4(), uuid4(), uuid4()
    fetched = datetime.now(UTC)

    row = MagicMock()
    row.topic = "rate cuts"
    row.vertical = "finance"
    row.evidence_pack = None
    row.status = None

    _install_fake_session_scope(monkeypatch, rows={did: row})

    spans = [
        RetrievedSpan(
            verbatim_span="The Fed cut rates by 25 bps.",
            char_start=10,
            char_end=10 + len("The Fed cut rates by 25 bps."),
            source_id=src1,
            fetched_at=fetched,
            trust_tier=2,
            score=0.9,
            entity_ids=[],
        ),
        RetrievedSpan(
            verbatim_span="Inflation cooled in Q4.",
            char_start=0,
            char_end=len("Inflation cooled in Q4."),
            source_id=src2,
            fetched_at=fetched,
            trust_tier=3,
            score=0.7,
            entity_ids=[],
        ),
        RetrievedSpan(
            verbatim_span="ECB held rates steady.",
            char_start=42,
            char_end=42 + len("ECB held rates steady."),
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

    baseline_called = {"flag": False}

    async def boom(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        baseline_called["flag"] = True
        return []

    monkeypatch.setattr(discussion_mod, "_baseline_evidence_pack", boom)

    result = await discussion_mod.assemble_evidence_pack(str(did))

    fake_retriever.retrieve.assert_awaited_once()
    args, kwargs = fake_retriever.retrieve.call_args
    assert args[0] == "rate cuts"
    assert kwargs["top_k"] == 20
    assert kwargs["recency_boost"] is True

    assert baseline_called["flag"] is False
    assert result["evidence_count"] == 3
    assert result["source"] == "hybrid"

    assert isinstance(row.evidence_pack, list)
    assert len(row.evidence_pack) == 3
    pack_texts = [e["verbatim_span"] for e in row.evidence_pack]
    assert pack_texts == [
        "The Fed cut rates by 25 bps.",
        "Inflation cooled in Q4.",
        "ECB held rates steady.",
    ]
    for entry, span in zip(row.evidence_pack, spans, strict=True):
        assert entry["source_id"] == str(span.source_id)
        assert entry["trust_tier"] == span.trust_tier
        assert entry["char_end"] - entry["char_start"] == len(span.verbatim_span)
        # The dict must be EvidenceRef-shaped — no score, no entity_ids.
        assert "score" not in entry
        assert "entity_ids" not in entry


@pytest.mark.asyncio
async def test_assemble_evidence_pack_falls_back_when_retriever_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argus_workers.activities import discussion as discussion_mod

    did = uuid4()
    row = MagicMock()
    row.topic = "topic"
    row.vertical = "geopolitics"
    row.evidence_pack = None
    row.status = None

    _install_fake_session_scope(monkeypatch, rows={did: row})

    fake_retriever = MagicMock()
    fake_retriever.retrieve = AsyncMock(return_value=[])
    monkeypatch.setattr(
        discussion_mod,
        "_build_hybrid_retriever",
        AsyncMock(return_value=fake_retriever),
    )

    baseline_calls = {"count": 0}

    async def fake_baseline(vertical: str, limit: int = 20) -> list[dict[str, Any]]:
        baseline_calls["count"] += 1
        return []

    monkeypatch.setattr(discussion_mod, "_baseline_evidence_pack", fake_baseline)

    result = await discussion_mod.assemble_evidence_pack(str(did))
    assert baseline_calls["count"] == 1
    assert result["source"] == "baseline"
    assert result["evidence_count"] == 0
