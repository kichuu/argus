"""Tests for /search.

Mocks ``session_scope`` (imported into ``argus_api.routes.search``) so that
queries return canned model objects, then asserts the response shape.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from argus_api.main import app
from argus_api.routes import search as search_route
from argus_core.db.models import (
    ClaimModel,
    DiscussionRunModel,
    EntityModel,
    SourceModel,
)
from httpx import ASGITransport, AsyncClient


# ---------- fakes ----------


class _FakeResult:
    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _FakeSession:
    """Returns ``items_for[model]`` from ``execute(select(model)...)``.

    The route's only ``execute`` calls are ``select(<Model>)`` queries; we
    inspect the FROM clause to figure out which model the test should answer
    for.
    """

    def __init__(self, items_for: dict[type, list]) -> None:
        self._items_for = items_for

    async def execute(self, stmt):
        # Find the model class we're selecting from.
        target = None
        cd = getattr(stmt, "column_descriptions", None) or []
        if cd:
            target = cd[0].get("entity")
        items = self._items_for.get(target, []) if isinstance(target, type) else []
        return _FakeResult(items)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _make_scope(session: _FakeSession):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


# ---------- row factories ----------


def _claim_row(statement: str = "Some statement about Ukraine relations.") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        statement=statement,
        status="likely_true",
        confidence=0.8,
        supporting_evidence=[],
        contradicting_evidence=[],
        affected_entities=[],
        agent_consensus={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _source_row(title: str = "Ukraine Daily", publisher: str = "BBC") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        url="https://example.com",
        feed_url=None,
        title=title,
        content_hash="abc",
        raw_text="",
        fetched_at=datetime.now(UTC),
        published_at=None,
        license=None,
        trust_tier=2,
        publisher=publisher,
        language="en",
    )


def _entity_row(name: str = "Ukraine") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        canonical_name=name,
        entity_type="country",
        wikidata_id=None,
        aliases=[],
        description=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _discussion_row(topic: str = "Ukraine ceasefire talks") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        topic=topic,
        vertical="geopolitics",
        status="planning",
        persona_ids=[],
        evidence_pack=[],
        final_claim_ids=[],
        started_at=datetime.now(UTC),
        completed_at=None,
        error=None,
    )


# ---------- tests ----------


@pytest.mark.asyncio
async def test_search_empty_q_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession({})
    monkeypatch.setattr(search_route, "session_scope", _make_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/search?q=")

    assert resp.status_code == 200
    body = resp.json()
    assert body["q"] == ""
    assert body["total"] == 0
    assert body["results"] == {
        "claims": [],
        "sources": [],
        "entities": [],
        "discussions": [],
    }


@pytest.mark.asyncio
async def test_search_single_char_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """q='x' is below MIN_QUERY_LEN — no fishing."""
    session = _FakeSession(
        {
            ClaimModel: [_claim_row()],
            SourceModel: [_source_row()],
            EntityModel: [_entity_row()],
            DiscussionRunModel: [_discussion_row()],
        }
    )
    monkeypatch.setattr(search_route, "session_scope", _make_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/search?q=x")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    for kind in ("claims", "sources", "entities", "discussions"):
        assert body["results"][kind] == []


@pytest.mark.asyncio
async def test_search_returns_hits_in_correct_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    claim = _claim_row("Ukraine signed a treaty on Tuesday with multiple partners.")
    source = _source_row(title="Ukraine Daily Briefing", publisher="Reuters")
    entity = _entity_row(name="Ukraine")
    discussion = _discussion_row(topic="Ukraine ceasefire talks")

    session = _FakeSession(
        {
            ClaimModel: [claim],
            SourceModel: [source],
            EntityModel: [entity],
            DiscussionRunModel: [discussion],
        }
    )
    monkeypatch.setattr(search_route, "session_scope", _make_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/search?q=ukraine")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["q"] == "ukraine"
    assert body["total"] == 4

    # Claims
    assert len(body["results"]["claims"]) == 1
    c = body["results"]["claims"][0]
    assert c["id"] == str(claim.id)
    assert c["href"] == "/synthesis"
    assert c["label"].startswith("Ukraine signed")
    assert len(c["label"]) <= 60
    assert len(c["snippet"]) <= 120

    # Sources
    assert len(body["results"]["sources"]) == 1
    s = body["results"]["sources"][0]
    assert s["id"] == str(source.id)
    assert s["href"] == "/sources"
    assert s["label"] == "Ukraine Daily Briefing"
    assert "Reuters" in s["snippet"]
    assert "trust tier" in s["snippet"]

    # Entities
    assert len(body["results"]["entities"]) == 1
    e = body["results"]["entities"][0]
    assert e["id"] == str(entity.id)
    assert e["href"] == "/kg"
    assert e["label"] == "Ukraine"
    assert e["snippet"] == "country"

    # Discussions
    assert len(body["results"]["discussions"]) == 1
    d = body["results"]["discussions"][0]
    assert d["id"] == str(discussion.id)
    assert d["href"] == "/synthesis"
    assert d["label"] == "Ukraine ceasefire talks"
    assert d["snippet"].startswith("planning")


@pytest.mark.asyncio
async def test_search_kinds_filter_only_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession(
        {
            ClaimModel: [_claim_row("Ukraine claim text here")],
            SourceModel: [_source_row()],
            EntityModel: [_entity_row()],
            DiscussionRunModel: [_discussion_row()],
        }
    )
    monkeypatch.setattr(search_route, "session_scope", _make_scope(session))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/search?q=ukraine&kinds=claims")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]["claims"]) == 1
    assert body["results"]["sources"] == []
    assert body["results"]["entities"] == []
    assert body["results"]["discussions"] == []
    assert body["total"] == 1
