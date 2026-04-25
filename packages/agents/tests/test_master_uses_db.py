"""Tests that MasterAgent reads personas from the DB instead of a hardcoded list.

Both `session_scope` and the LLM provider are mocked. No real DB or network.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from argus_agents import master as master_module
from argus_agents.master import MasterAgent, _PersonaSelection, color_for_frame
from argus_agents.state import DiscussionState, EvidencePack
from argus_core.schemas import EvidenceRef
from argus_extraction.providers import Provider
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _make_span(text: str = "an evidence span") -> EvidenceRef:
    return EvidenceRef(
        source_id=uuid4(),
        verbatim_span=text,
        char_start=0,
        char_end=len(text),
        fetched_at=datetime.now(UTC),
        trust_tier=2,
    )


def _make_persona_row(frame: str, **overrides) -> SimpleNamespace:
    base = {
        "id": uuid4(),
        "frame": frame,
        "description": f"description for {frame}",
        "knowledge_emphasis": ["a", "b"],
        "temperature": 0.7,
        "redlines": [],
        "bias": None,
        "model_assignment": None,
        "color": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeResult:
    def __init__(self, items: list) -> None:
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _FakeSession:
    def __init__(self, items: list) -> None:
        self._items = items

    async def execute(self, stmt):
        return _FakeResult(self._items)


def _patch_session(monkeypatch: pytest.MonkeyPatch, items: list) -> None:
    @asynccontextmanager
    async def _scope():
        yield _FakeSession(items)

    monkeypatch.setattr(master_module, "session_scope", _scope)


class _StubProvider(Provider):
    name = "openai"

    def __init__(self, response: BaseModel | Exception | None = None) -> None:
        self._response = response
        self.structured_calls: list[tuple[str, type[BaseModel], str]] = []

    async def structured_extract(
        self, prompt: str, schema: type[BaseModel], model: str
    ) -> BaseModel:
        self.structured_calls.append((prompt, schema, model))
        if isinstance(self._response, Exception):
            raise self._response
        if self._response is None:
            raise AssertionError("no scripted response")
        return self._response

    async def text_complete(self, prompt: str, model: str, max_tokens: int = 512) -> str:
        raise NotImplementedError


def _make_state() -> DiscussionState:
    return DiscussionState(
        discussion_id=uuid4(),
        topic="should retail CBDC be deployed",
        evidence_pack=EvidencePack(
            topic="should retail CBDC be deployed",
            evidence=[_make_span("a span"), _make_span("another span")],
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_master_uses_db_personas(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _make_persona_row("skeptical empiricist"),
        _make_persona_row("regulator viewpoint"),
        _make_persona_row("operator on the ground"),
        _make_persona_row("historical analogue analyst"),
        _make_persona_row("affected-stakeholder advocate"),
    ]
    _patch_session(monkeypatch, rows)

    selection = _PersonaSelection(
        chosen_persona_ids=[str(rows[0].id), str(rows[1].id), str(rows[3].id)]
    )
    provider = _StubProvider(selection)

    agent = MasterAgent(provider, model="gpt-4.1")
    state = _make_state()
    state = await agent.step(state)

    chosen_frames = {p.frame for p in state.personas}
    assert 3 <= len(state.personas) <= 5
    assert chosen_frames == {
        "skeptical empiricist",
        "regulator viewpoint",
        "historical analogue analyst",
    }
    # And the personas were indeed translated from DB rows (ids match).
    chosen_ids = {p.id for p in state.personas}
    expected_ids = {rows[0].id, rows[1].id, rows[3].id}
    assert chosen_ids == expected_ids
    # Color should be derived since DB color is null.
    for p in state.personas:
        assert p.color is not None
        assert p.color == color_for_frame(p.frame)
    # A master message was appended.
    assert state.messages, "master should append a cast message"
    assert state.messages[-1].role.value == "master"
    assert "Cast" in state.messages[-1].content


@pytest.mark.asyncio
async def test_master_falls_back_when_db_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_session(monkeypatch, [])

    # Provider should not be called in the empty-DB path; assert that.
    provider = _StubProvider(response=AssertionError("LLM should not be invoked"))

    agent = MasterAgent(provider, model="gpt-4.1")
    state = _make_state()
    state = await agent.step(state)

    assert len(state.personas) == 3
    frames = {p.frame for p in state.personas}
    assert frames == {
        "skeptical empiricist",
        "regulator viewpoint",
        "operator on the ground",
    }
    # Provider was not called.
    assert provider.structured_calls == []


@pytest.mark.asyncio
async def test_master_falls_back_to_recent_db_when_llm_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        _make_persona_row("skeptical empiricist"),
        _make_persona_row("regulator viewpoint"),
        _make_persona_row("operator on the ground"),
        _make_persona_row("historical analogue analyst"),
    ]
    _patch_session(monkeypatch, rows)

    provider = _StubProvider(response=RuntimeError("boom"))

    agent = MasterAgent(provider, model="gpt-4.1")
    state = _make_state()
    state = await agent.step(state)

    # Falls back to the recent DB rows; should be 3-5 personas, all DB-sourced.
    assert 3 <= len(state.personas) <= 5
    chosen_ids = {p.id for p in state.personas}
    db_ids = {r.id for r in rows}
    assert chosen_ids.issubset(db_ids)


@pytest.mark.asyncio
async def test_master_uses_db_color_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _make_persona_row("skeptical empiricist", color="#abc123"),
        _make_persona_row("regulator viewpoint"),
        _make_persona_row("operator on the ground"),
    ]
    _patch_session(monkeypatch, rows)
    selection = _PersonaSelection(
        chosen_persona_ids=[str(r.id) for r in rows]
    )
    provider = _StubProvider(selection)
    agent = MasterAgent(provider, model="gpt-4.1")

    state = await agent.step(_make_state())

    by_frame = {p.frame: p for p in state.personas}
    assert by_frame["skeptical empiricist"].color == "#abc123"
    # The other two derive their color since DB.color is null.
    assert by_frame["regulator viewpoint"].color == color_for_frame("regulator viewpoint")
