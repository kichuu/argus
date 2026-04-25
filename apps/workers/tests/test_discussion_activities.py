from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from argus_core.db.models import DiscussionRunModel
from argus_core.schemas import (
    AgentMessage,
    AgentRole,
    Claim,
    ClaimStatus,
    DiscussionStatus,
    EvidenceRef,
)
from argus_workers.activities import discussion as discussion_module


class _FakeRow:
    def __init__(
        self,
        *,
        id: UUID,
        topic: str = "topic",
        vertical: str = "finance",
        status: str = DiscussionStatus.PLANNING.value,
    ) -> None:
        self.id = id
        self.topic = topic
        self.vertical = vertical
        self.status = status
        self.evidence_pack: list[dict[str, Any]] = []
        self.persona_ids: list[str] = []
        self.final_claim_ids: list[str] = []
        self.completed_at: datetime | None = None
        self.error: str | None = None


class _FakeSession:
    def __init__(self, rows_by_id: dict[UUID, _FakeRow] | None = None) -> None:
        self.rows_by_id: dict[UUID, _FakeRow] = rows_by_id or {}
        self.added: list[Any] = []

    async def get(self, _model: Any, ident: UUID) -> Any:
        return self.rows_by_id.get(ident)

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        if isinstance(obj, DiscussionRunModel):
            self.rows_by_id[obj.id] = obj


def _make_session_factory(session: _FakeSession) -> Any:
    @asynccontextmanager
    async def _factory() -> Any:
        yield session

    return _factory


def _ev_ref() -> EvidenceRef:
    return EvidenceRef(
        source_id=uuid4(),
        verbatim_span="The Fed held rates.",
        char_start=0,
        char_end=len("The Fed held rates."),
        fetched_at=datetime.now(UTC),
        trust_tier=2,
    )


def _claim() -> Claim:
    return Claim(
        statement="The Fed held rates at 5.25-5.50% on Dec 18 2024.",
        status=ClaimStatus.LIKELY_TRUE,
        confidence=0.84,
        supporting_evidence=[_ev_ref()],
    )


def _msg(discussion_id: UUID) -> AgentMessage:
    return AgentMessage(
        discussion_id=discussion_id,
        agent_id="research-1",
        role=AgentRole.RESEARCH,
        content="research notes here",
        evidence_refs=[_ev_ref()],
    )


@pytest.mark.asyncio
async def test_start_discussion_creates_new_row(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    did = await discussion_module.start_discussion(
        {"topic": "Topic A", "vertical": "finance"},
    )

    parsed = UUID(did)
    assert parsed in session.rows_by_id
    row = session.rows_by_id[parsed]
    assert row.topic == "Topic A"
    assert row.vertical == "finance"
    assert row.status == DiscussionStatus.PLANNING.value
    assert session.added and session.added[0] is row


@pytest.mark.asyncio
async def test_start_discussion_resets_existing_row(monkeypatch: pytest.MonkeyPatch) -> None:
    did = uuid4()
    existing = _FakeRow(id=did, status=DiscussionStatus.FAILED.value)
    existing.error = "old error"
    session = _FakeSession({did: existing})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    out = await discussion_module.start_discussion(
        {
            "topic": "Topic B",
            "vertical": "geopolitics",
            "discussion_id": str(did),
        },
    )

    assert out == str(did)
    assert existing.topic == "Topic B"
    assert existing.vertical == "geopolitics"
    assert existing.status == DiscussionStatus.PLANNING.value
    assert existing.error is None
    # Existing row should not be re-added.
    assert session.added == []


@pytest.mark.asyncio
async def test_assemble_evidence_pack_persists_serialized_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    did = uuid4()
    row = _FakeRow(id=did, topic="Did the Fed hold rates?")
    session = _FakeSession({did: row})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    span_a = MagicMock()
    ref = _ev_ref()
    span_a.source_id = ref.source_id
    span_a.verbatim_span = ref.verbatim_span
    span_a.char_start = ref.char_start
    span_a.char_end = ref.char_end
    span_a.fetched_at = ref.fetched_at
    span_a.trust_tier = ref.trust_tier

    fake_retriever = MagicMock()
    fake_retriever.retrieve = AsyncMock(return_value=[span_a])
    monkeypatch.setattr(discussion_module, "_build_retriever", lambda: fake_retriever)

    summary = await discussion_module.assemble_evidence_pack(str(did))

    assert summary == {"discussion_id": str(did), "n_evidence": 1}
    assert row.status == DiscussionStatus.RESEARCHING.value
    assert len(row.evidence_pack) == 1
    persisted = row.evidence_pack[0]
    assert persisted["verbatim_span"] == ref.verbatim_span
    assert persisted["trust_tier"] == ref.trust_tier
    fake_retriever.retrieve.assert_awaited_once()


@pytest.mark.asyncio
async def test_assemble_evidence_pack_skips_invalid_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    did = uuid4()
    row = _FakeRow(id=did, topic="Topic C")
    session = _FakeSession({did: row})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    bad = MagicMock()
    bad.source_id = uuid4()
    bad.verbatim_span = "X"
    bad.char_start = 0
    bad.char_end = 10  # mismatched length -> EvidenceRef rejects
    bad.fetched_at = datetime.now(UTC)
    bad.trust_tier = 2

    good_ref = _ev_ref()
    good = MagicMock()
    good.source_id = good_ref.source_id
    good.verbatim_span = good_ref.verbatim_span
    good.char_start = good_ref.char_start
    good.char_end = good_ref.char_end
    good.fetched_at = good_ref.fetched_at
    good.trust_tier = good_ref.trust_tier

    fake_retriever = MagicMock()
    fake_retriever.retrieve = AsyncMock(return_value=[bad, good])
    monkeypatch.setattr(discussion_module, "_build_retriever", lambda: fake_retriever)

    summary = await discussion_module.assemble_evidence_pack(str(did))

    assert summary["n_evidence"] == 1
    assert len(row.evidence_pack) == 1


@pytest.mark.asyncio
async def test_run_discussion_graph_persists_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    did = uuid4()
    row = _FakeRow(id=did, topic="Topic D")
    session = _FakeSession({did: row})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    state = MagicMock()
    state.personas = []
    state.messages = [_msg(did), _msg(did)]
    state.final_claims = [_claim()]

    fake_orch = MagicMock()
    fake_orch.run = AsyncMock(return_value=state)
    monkeypatch.setattr(discussion_module, "_build_retriever", lambda: MagicMock())
    monkeypatch.setattr(
        discussion_module,
        "_build_orchestrator",
        lambda _r, **_kw: fake_orch,
    )

    fake_pubsub = MagicMock()
    fake_pubsub.publish = AsyncMock()
    fake_pubsub.close = AsyncMock()
    from argus_core import pubsub as pubsub_module

    monkeypatch.setattr(
        pubsub_module, "DiscussionPubSub", lambda *_, **__: fake_pubsub
    )

    result = await discussion_module.run_discussion_graph(str(did))

    assert result["n_messages"] == 2
    assert result["n_claims"] == 1
    assert len(result["final_claims"]) == 1
    assert row.status == DiscussionStatus.SYNTHESIZING.value
    persisted_messages = [a for a in session.added if hasattr(a, "agent_id")]
    assert len(persisted_messages) == 2
    fake_orch.run.assert_awaited_once_with("Topic D", vertical="finance", discussion_id=did)
    fake_pubsub.close.assert_awaited()


@pytest.mark.asyncio
async def test_persist_results_writes_claims_and_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    did = uuid4()
    row = _FakeRow(id=did)
    session = _FakeSession({did: row})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    claim_dict = _claim().model_dump(mode="json")

    summary = await discussion_module.persist_results(
        {
            "discussion_id": str(did),
            "final_claims": [claim_dict],
        },
    )

    assert summary == {"discussion_id": str(did), "n_claims_persisted": 1}
    assert row.status == DiscussionStatus.COMPLETED.value
    assert row.completed_at is not None
    persisted_claims = [a for a in session.added if hasattr(a, "statement")]
    assert len(persisted_claims) == 1
    pc = persisted_claims[0]
    assert pc.statement == claim_dict["statement"]
    assert pc.confidence == pytest.approx(claim_dict["confidence"])
    assert isinstance(pc.supporting_evidence, list)


@pytest.mark.asyncio
async def test_persist_results_handles_no_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    did = uuid4()
    row = _FakeRow(id=did)
    session = _FakeSession({did: row})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    summary = await discussion_module.persist_results(
        {"discussion_id": str(did), "final_claims": []},
    )

    assert summary["n_claims_persisted"] == 0
    assert row.status == DiscussionStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_mark_failed_updates_status(monkeypatch: pytest.MonkeyPatch) -> None:
    did = uuid4()
    row = _FakeRow(id=did, status=DiscussionStatus.DEBATING.value)
    session = _FakeSession({did: row})
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    out = await discussion_module._mark_failed(
        {"id": str(did), "error": "kaboom"},
    )

    assert out["marked"] is True
    assert row.status == DiscussionStatus.FAILED.value
    assert row.error == "kaboom"
    assert row.completed_at is not None


@pytest.mark.asyncio
async def test_mark_failed_missing_row(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(discussion_module, "session_scope", _make_session_factory(session))

    out = await discussion_module._mark_failed(
        {"id": str(uuid4()), "error": "missing"},
    )
    assert out["marked"] is False
