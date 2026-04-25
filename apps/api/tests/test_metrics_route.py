"""Tests for /metrics/* — overview, traces, evals.

Mocks ``session_scope`` (imported into the metrics route module) to yield a
fake AsyncSession that returns canned model rows. Eval-baseline lookups are
patched to control the hallucination_rate / missing-file branches.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from argus_api.main import app
from argus_api.routes import metrics as metrics_route
from httpx import ASGITransport, AsyncClient

# ---------- Fake session ----------


class _FakeResult:
    def __init__(self, items: list, scalar: Any = None) -> None:
        self._items = items
        self._scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def scalar_one(self):
        return self._scalar


class _FakeSession:
    """Returns canned data based on the SQL the route emits.

    The metrics route issues a small set of distinct queries; we route them by
    inspecting the compiled SQL string for keywords (FROM table, status filter).
    """

    def __init__(
        self,
        *,
        discussion_rows: list,
        claim_rows: list,
        failed_rows: list,
        total_disc: int,
        failed_disc: int,
        claims_total: int,
        verified_total: int,
        sources_total: int,
        sources_24h: int,
    ) -> None:
        self.discussion_rows = discussion_rows
        self.claim_rows = claim_rows
        self.failed_rows = failed_rows
        self.total_disc = total_disc
        self.failed_disc = failed_disc
        self.claims_total = claims_total
        self.verified_total = verified_total
        self.sources_total = sources_total
        self.sources_24h = sources_24h

    async def execute(self, stmt):
        try:
            sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()
        except Exception:
            sql = str(stmt).lower()
        # COUNT queries
        if "count(" in sql:
            if "discussion_runs" in sql:
                if "failed" in sql:
                    return _FakeResult([], scalar=self.failed_disc)
                return _FakeResult([], scalar=self.total_disc)
            if "claims" in sql:
                if "likely_true" in sql:
                    return _FakeResult([], scalar=self.verified_total)
                return _FakeResult([], scalar=self.claims_total)
            if "sources" in sql:
                if "fetched_at" in sql:
                    return _FakeResult([], scalar=self.sources_24h)
                return _FakeResult([], scalar=self.sources_total)
            return _FakeResult([], scalar=0)

        # SELECT row queries
        if "discussion_runs" in sql:
            if "failed" in sql:
                return _FakeResult(self.failed_rows)
            return _FakeResult(self.discussion_rows)
        if "claims" in sql:
            return _FakeResult(self.claim_rows)
        return _FakeResult([])

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def _make_session_scope(session: _FakeSession):
    @asynccontextmanager
    async def _scope():
        yield session

    return _scope


# ---------- Row builders ----------


def _disc(status: str = "completed", started_offset_min: int = 30, latency_s: float = 12.4):
    started = datetime.now(UTC) - timedelta(minutes=started_offset_min)
    completed = (
        started + timedelta(seconds=latency_s) if status in ("completed", "failed") else None
    )
    return SimpleNamespace(
        id=uuid4(),
        topic="t",
        vertical="geopolitics",
        status=status,
        started_at=started,
        completed_at=completed,
    )


def _claim(status: str = "likely_true", offset_min: int = 30):
    return SimpleNamespace(
        id=uuid4(),
        statement="x",
        status=status,
        confidence=0.9,
        created_at=datetime.now(UTC) - timedelta(minutes=offset_min),
    )


# ---------- Tests ----------


@pytest.mark.asyncio
async def test_overview_shape_with_eval_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _FakeSession(
        discussion_rows=[_disc(), _disc(started_offset_min=120)],
        claim_rows=[_claim(), _claim(status="unverified")],
        failed_rows=[_disc(status="failed", started_offset_min=60)],
        total_disc=10,
        failed_disc=1,
        claims_total=2,
        verified_total=1,
        sources_total=5,
        sources_24h=3,
    )
    monkeypatch.setattr(metrics_route, "session_scope", _make_session_scope(sess))
    monkeypatch.setattr(
        metrics_route,
        "_read_eval_baseline",
        lambda: {"hallucination_rate": 0.04, "n_gold": 10, "_meta": {"captured_at": "2026-04-25"}},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/overview")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # All required keys present
    expected_keys = {
        "debates_24h",
        "claims_24h",
        "claims_total",
        "sources_24h",
        "sources_total",
        "verified_rate",
        "hallucination_rate",
        "tok_24h_est",
        "cost_24h_est_usd",
        "err_rate",
        "spark_debates",
        "spark_claims",
        "spark_cost",
        "spark_err",
    }
    assert expected_keys.issubset(body.keys())

    assert body["debates_24h"] == 2
    assert body["claims_total"] == 2
    assert body["claims_24h"] == 2
    assert body["sources_total"] == 5
    assert body["sources_24h"] == 3
    assert body["verified_rate"] == pytest.approx(0.5)
    assert body["err_rate"] == pytest.approx(0.1)
    assert body["hallucination_rate"] == pytest.approx(0.04)
    assert body["tok_24h_est"] == 2 * 30_000 + 2 * 8_000
    assert isinstance(body["cost_24h_est_usd"], float)
    assert len(body["spark_debates"]) == 12
    assert len(body["spark_claims"]) == 12
    assert len(body["spark_cost"]) == 12
    assert len(body["spark_err"]) == 12


@pytest.mark.asyncio
async def test_overview_handles_zero_state(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _FakeSession(
        discussion_rows=[],
        claim_rows=[],
        failed_rows=[],
        total_disc=0,
        failed_disc=0,
        claims_total=0,
        verified_total=0,
        sources_total=0,
        sources_24h=0,
    )
    monkeypatch.setattr(metrics_route, "session_scope", _make_session_scope(sess))
    monkeypatch.setattr(metrics_route, "_read_eval_baseline", lambda: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["debates_24h"] == 0
    assert body["verified_rate"] is None
    assert body["err_rate"] is None
    assert body["hallucination_rate"] is None
    assert body["tok_24h_est"] == 0
    assert body["cost_24h_est_usd"] == 0.0


@pytest.mark.asyncio
async def test_traces_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _disc(status="completed", started_offset_min=10, latency_s=12.4),
        _disc(status="failed", started_offset_min=60, latency_s=2.1),
        _disc(status="planning", started_offset_min=2),
    ]
    sess = _FakeSession(
        discussion_rows=rows,
        claim_rows=[],
        failed_rows=[],
        total_disc=3,
        failed_disc=1,
        claims_total=0,
        verified_total=0,
        sources_total=0,
        sources_24h=0,
    )
    monkeypatch.setattr(metrics_route, "session_scope", _make_session_scope(sess))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/traces?limit=10")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "traces" in body
    assert isinstance(body["traces"], list)
    assert len(body["traces"]) == 3

    first = body["traces"][0]
    expected_keys = {
        "id",
        "label",
        "model",
        "tokens_est",
        "cost_est_usd",
        "latency_seconds",
        "status",
    }
    assert expected_keys.issubset(first.keys())
    # status mapping
    statuses = [t["status"] for t in body["traces"]]
    assert "ok" in statuses  # completed -> ok
    assert "fail" in statuses  # failed -> fail
    # planning passes through
    assert "planning" in statuses
    # Failed run zeroed out
    failed_trace = next(t for t in body["traces"] if t["status"] == "fail")
    assert failed_trace["tokens_est"] == 0


@pytest.mark.asyncio
async def test_evals_with_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        metrics_route,
        "_read_eval_baseline",
        lambda: {
            "citation_recall": 0.91,
            "exact_match_rate": 0.4,
            "hallucination_rate": 0.0,
            "n_gold": 10,
            "_meta": {"captured_at": "2026-04-25"},
        },
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/evals")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    expected_keys = {
        "consensus_quality",
        "citation_coverage",
        "persona_drift",
        "synth_faithfulness",
        "hallucination_rate",
        "n_gold",
        "last_run",
    }
    assert expected_keys == set(body.keys())
    assert body["consensus_quality"] is None  # not yet computed
    assert body["persona_drift"] is None
    assert body["citation_coverage"] == pytest.approx(0.91)
    assert body["synth_faithfulness"] == pytest.approx(0.4)
    assert body["hallucination_rate"] == 0.0
    assert body["n_gold"] == 10
    assert body["last_run"] == "2026-04-25"


@pytest.mark.asyncio
async def test_evals_missing_baseline_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """When results_baseline.json is absent, every numeric field is null."""
    monkeypatch.setattr(metrics_route, "_read_eval_baseline", lambda: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/evals")

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "consensus_quality": None,
        "citation_coverage": None,
        "persona_drift": None,
        "synth_faithfulness": None,
        "hallucination_rate": None,
        "n_gold": None,
        "last_run": None,
    }
