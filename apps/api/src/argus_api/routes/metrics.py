"""Observability metrics — DB-derived counts, sparklines, traces, evals.

Powers the ObsScreen on the frontend. Three endpoints:

- ``GET /metrics/overview``  KPI cards + 12-hour hourly sparklines.
- ``GET /metrics/traces``    recent discussion runs as trace rows.
- ``GET /metrics/evals``     eval baseline metrics from ``eval/results_baseline.json``.

Token / cost figures are heuristics (we don't yet persist real token usage):
    tokens_per_claim ~ 30k, tokens_per_discussion ~ 8k, $/1M ~ 2.0 (gpt-4.1).
Consensus quality / persona drift are intentionally null until those evaluators
ship.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from argus_core.db.models import ClaimModel, DiscussionRunModel, SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import get_logger
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

logger = get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# --- heuristics ---------------------------------------------------------------

TOKENS_PER_CLAIM = 30_000
TOKENS_PER_DISCUSSION = 8_000
TOKENS_PER_TRACE = 8_200  # baseline per-trace estimate when more is unknown
COST_PER_MTOK_USD = 2.0   # gpt-4.1 ballpark (in/out blended)
SPARK_BUCKETS = 12         # 12 hourly buckets ending now


def _est_cost_usd(tokens: int) -> float:
    return round(tokens / 1_000_000 * COST_PER_MTOK_USD, 4)


# --- response models ----------------------------------------------------------


class MetricsOverview(BaseModel):
    debates_24h: int
    claims_24h: int
    claims_total: int
    sources_24h: int
    sources_total: int
    verified_rate: float | None
    hallucination_rate: float | None
    tok_24h_est: int
    cost_24h_est_usd: float
    err_rate: float | None
    spark_debates: list[int]
    spark_claims: list[int]
    spark_cost: list[float]
    spark_err: list[float]


class TraceRow(BaseModel):
    id: str
    label: str
    model: str
    tokens_est: int
    cost_est_usd: float
    latency_seconds: float | None
    status: str


class MetricsTraces(BaseModel):
    traces: list[TraceRow]


class MetricsEvals(BaseModel):
    consensus_quality: float | None
    citation_coverage: float | None
    persona_drift: float | None
    synth_faithfulness: float | None
    hallucination_rate: float | None
    n_gold: int | None
    last_run: str | None


# --- helpers ------------------------------------------------------------------


def _hourly_buckets(timestamps: list[datetime], now: datetime) -> list[int]:
    """Bucket a list of timestamps into ``SPARK_BUCKETS`` hourly slots ending at ``now``.

    Bucket 0 is the oldest (now - 12h .. now - 11h); the last bucket covers the
    current hour. Anything outside the window is dropped.
    """
    buckets = [0] * SPARK_BUCKETS
    window_start = now - timedelta(hours=SPARK_BUCKETS)
    for ts in timestamps:
        if ts is None:
            continue
        # Ensure tz-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts < window_start or ts > now:
            continue
        delta = now - ts
        idx = SPARK_BUCKETS - 1 - int(delta.total_seconds() // 3600)
        if 0 <= idx < SPARK_BUCKETS:
            buckets[idx] += 1
    return buckets


def _read_eval_baseline() -> dict[str, Any] | None:
    """Locate ``eval/results_baseline.json`` walking up from this file.

    Returns ``None`` if the file is missing or unreadable.
    """
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        candidate = parent / "eval" / "results_baseline.json"
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("metrics.eval_baseline.unreadable", error=str(exc))
                return None
    return None


# --- routes -------------------------------------------------------------------


@router.get("/overview", response_model=MetricsOverview)
async def metrics_overview() -> MetricsOverview:
    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_window = now - timedelta(hours=SPARK_BUCKETS)

    async with session_scope() as session:
        # Debates 24h + sparkline source
        debates_24h_rows = (
            await session.execute(
                select(DiscussionRunModel).where(DiscussionRunModel.started_at >= cutoff_window)
            )
        ).scalars().all()
        debate_starts = [r.started_at for r in debates_24h_rows]
        debates_24h = sum(1 for ts in debate_starts if ts is not None and (ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts) >= cutoff_24h)

        # All discussion rows (for err rate)
        total_disc = int(
            (await session.execute(select(func.count()).select_from(DiscussionRunModel))).scalar_one() or 0
        )
        failed_disc = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(DiscussionRunModel)
                    .where(DiscussionRunModel.status == "failed")
                )
            ).scalar_one()
            or 0
        )
        err_rate = (failed_disc / total_disc) if total_disc else None

        # Errors sparkline (failed discussion runs by hour)
        failed_rows_window = (
            await session.execute(
                select(DiscussionRunModel).where(
                    DiscussionRunModel.status == "failed",
                    DiscussionRunModel.started_at >= cutoff_window,
                )
            )
        ).scalars().all()

        # Claims
        claims_total = int(
            (await session.execute(select(func.count()).select_from(ClaimModel))).scalar_one() or 0
        )
        claim_rows_window = (
            await session.execute(
                select(ClaimModel).where(ClaimModel.created_at >= cutoff_window)
            )
        ).scalars().all()
        claim_starts = [r.created_at for r in claim_rows_window]
        claims_24h = sum(
            1
            for ts in claim_starts
            if ts is not None
            and (ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts) >= cutoff_24h
        )

        verified_total = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(ClaimModel)
                    .where(ClaimModel.status == "likely_true")
                )
            ).scalar_one()
            or 0
        )
        verified_rate = (verified_total / claims_total) if claims_total else None

        # Sources
        sources_total = int(
            (await session.execute(select(func.count()).select_from(SourceModel))).scalar_one() or 0
        )
        sources_24h = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(SourceModel)
                    .where(SourceModel.fetched_at >= cutoff_24h)
                )
            ).scalar_one()
            or 0
        )

    # Sparklines
    spark_debates = _hourly_buckets(debate_starts, now)
    spark_claims = _hourly_buckets(claim_starts, now)
    failed_starts = [r.started_at for r in failed_rows_window]
    spark_err_counts = _hourly_buckets(failed_starts, now)
    # Convert err counts to ratio per bucket using hourly debate count as the denom.
    spark_err: list[float] = []
    for f, d in zip(spark_err_counts, spark_debates, strict=False):
        spark_err.append(round(f / d, 4) if d else 0.0)

    # Cost sparkline derived from claims+debates per bucket via the same heuristic.
    spark_cost: list[float] = []
    for c, d in zip(spark_claims, spark_debates, strict=False):
        toks = c * TOKENS_PER_CLAIM + d * TOKENS_PER_DISCUSSION
        spark_cost.append(_est_cost_usd(toks))

    tok_24h_est = claims_24h * TOKENS_PER_CLAIM + debates_24h * TOKENS_PER_DISCUSSION
    cost_24h_est_usd = _est_cost_usd(tok_24h_est)

    # Hallucination rate: pulled from eval baseline if present.
    eval_baseline = _read_eval_baseline()
    hallucination_rate: float | None = None
    if eval_baseline is not None:
        raw = eval_baseline.get("hallucination_rate")
        if isinstance(raw, int | float):
            hallucination_rate = float(raw)

    return MetricsOverview(
        debates_24h=debates_24h,
        claims_24h=claims_24h,
        claims_total=claims_total,
        sources_24h=sources_24h,
        sources_total=sources_total,
        verified_rate=round(verified_rate, 4) if verified_rate is not None else None,
        hallucination_rate=hallucination_rate,
        tok_24h_est=tok_24h_est,
        cost_24h_est_usd=cost_24h_est_usd,
        err_rate=round(err_rate, 4) if err_rate is not None else None,
        spark_debates=spark_debates,
        spark_claims=spark_claims,
        spark_cost=spark_cost,
        spark_err=spark_err,
    )


@router.get("/traces", response_model=MetricsTraces)
async def metrics_traces(limit: int = Query(20, ge=1, le=200)) -> MetricsTraces:
    """Most-recent discussion runs as trace rows."""
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(DiscussionRunModel)
                .order_by(DiscussionRunModel.started_at.desc())
                .limit(limit)
            )
        ).scalars().all()

    traces: list[TraceRow] = []
    for r in rows:
        # Map status: completed -> ok, failed -> fail, anything else passes through as-is.
        if r.status == "completed":
            status_label = "ok"
        elif r.status == "failed":
            status_label = "fail"
        else:
            status_label = r.status

        # Latency
        latency: float | None = None
        if r.completed_at is not None and r.started_at is not None:
            try:
                latency = round((r.completed_at - r.started_at).total_seconds(), 2)
            except (TypeError, AttributeError):
                latency = None

        # Heuristic token / cost; if failed, zero out.
        tokens_est = 0 if r.status == "failed" else TOKENS_PER_TRACE
        cost_est = _est_cost_usd(tokens_est)

        # ID label: "d-YYYY-MM-DD-XX·VERTICAL" style; fall back to row id.
        short_id = str(r.id)[:8]
        if r.started_at is not None:
            day = r.started_at.strftime("%Y-%m-%d")
            label_id = f"d-{day}-{short_id}"
        else:
            label_id = f"d-{short_id}"

        traces.append(
            TraceRow(
                id=label_id,
                label=(r.vertical or "ORCH").upper(),
                model="gpt-4.1",
                tokens_est=tokens_est,
                cost_est_usd=cost_est,
                latency_seconds=latency,
                status=status_label,
            )
        )

    return MetricsTraces(traces=traces)


@router.get("/evals", response_model=MetricsEvals)
async def metrics_evals() -> MetricsEvals:
    baseline = _read_eval_baseline()
    if baseline is None:
        return MetricsEvals(
            consensus_quality=None,
            citation_coverage=None,
            persona_drift=None,
            synth_faithfulness=None,
            hallucination_rate=None,
            n_gold=None,
            last_run=None,
        )

    def _get_float(key: str) -> float | None:
        raw = baseline.get(key)
        return float(raw) if isinstance(raw, int | float) else None

    n_gold_raw = baseline.get("n_gold")
    n_gold = int(n_gold_raw) if isinstance(n_gold_raw, int | float) else None

    captured_at = None
    meta = baseline.get("_meta")
    if isinstance(meta, dict):
        captured_at = meta.get("captured_at")

    return MetricsEvals(
        consensus_quality=None,
        citation_coverage=_get_float("citation_recall"),
        persona_drift=None,
        synth_faithfulness=_get_float("exact_match_rate"),
        hallucination_rate=_get_float("hallucination_rate"),
        n_gold=n_gold,
        last_run=captured_at,
    )
