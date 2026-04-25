"""Run the full Phase 4 Argus pipeline against a single RSS feed, end-to-end.

Stages: ingest -> extract -> verify -> index -> start_discussion ->
assemble_evidence_pack -> run_discussion_graph -> persist_results -> ledger.

The Temporal worker calls these same activities in production. This runner
invokes the underlying async functions directly so you can demo the full
fetch -> debate -> persist path without `temporal server start-dev`.

Usage:
    uv run python scripts/run_full_demo.py \
        --rss https://feeds.bbci.co.uk/news/world/rss.xml \
        --topic "What does this week's news mean for NATO posture toward Russia?"

    # Skip the (expensive) multi-agent debate and behave like run_baseline.py:
    uv run python scripts/run_full_demo.py --rss <url> --topic "..." --skip-discuss
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from typing import Any
from uuid import UUID

from argus_core.db.models import ClaimModel, SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import configure_logging
from argus_workers.activities.discussion import (
    assemble_evidence_pack,
    persist_results,
    run_discussion_graph,
    start_discussion,
)
from argus_workers.activities.extract import extract_claims
from argus_workers.activities.fetch import fetch_source, index_evidence
from argus_workers.activities.verify import verify_claims


# ---------------------------------------------------------------------------
# pretty-printing
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, msg: str) -> str:
    if not _USE_COLOR:
        return msg
    return f"\033[{code}m{msg}\033[0m"


def _green(msg: str) -> str:
    return _c("32", msg)


def _yellow(msg: str) -> str:
    return _c("33", msg)


def _red(msg: str) -> str:
    return _c("31", msg)


def _bold(msg: str) -> str:
    return _c("1", msg)


def _section(idx: int, total: int, label: str) -> None:
    print()
    print(_bold(f"[{idx}/{total}] {label}"))


def _ok(msg: str) -> None:
    print(f"  {_green('OK')}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_yellow('WARN')}  {msg}")


def _err(msg: str) -> None:
    print(f"  {_red('ERR')}  {msg}")


# ---------------------------------------------------------------------------
# activity-call helper (handles temporalio's @activity.defn wrapper)
# ---------------------------------------------------------------------------


async def _call(fn, *args):
    """Call an activity function whether or not temporalio exposes __wrapped__."""
    try:
        return await fn.__wrapped__(*args)  # type: ignore[attr-defined]
    except AttributeError:
        return await fn(*args)


# ---------------------------------------------------------------------------
# DB read helpers (read-only display)
# ---------------------------------------------------------------------------


async def _show_source(source_id: str) -> None:
    async with session_scope() as session:
        row = await session.get(SourceModel, UUID(source_id))
        if row is None:
            _warn(f"source {source_id[:8]} not found in DB")
            return
        print(
            f"    source {source_id[:8]}  trust={row.trust_tier}  "
            f"publisher={row.publisher!r}"
        )
        print(f"      title: {(row.title or '')[:80]}")
        print(f"      chars: {len(row.raw_text or '')}")


async def _show_claim(claim_id: str) -> None:
    async with session_scope() as session:
        row = await session.get(ClaimModel, UUID(claim_id))
        if row is None:
            return
        ev = row.supporting_evidence[0] if row.supporting_evidence else {}
        span = (ev.get("verbatim_span") or "")[:120]
        print(
            f"    claim {claim_id[:8]}  status={row.status}  "
            f"conf={row.confidence:.2f}"
        )
        print(f"      statement: {(row.statement or '')[:120]}")
        if span:
            print(f"      span:      {span!r}")


async def _show_final_ledger(discussion_id: str, final_claims: list[dict[str, Any]]) -> None:
    if not final_claims:
        _warn("no final claims emitted by the discussion graph")
        return
    print(f"    discussion={discussion_id}  final_claims={len(final_claims)}")
    for fc in final_claims:
        cid = fc.get("id")
        statement = (fc.get("statement") or "")[:140]
        status = fc.get("status", "?")
        conf = fc.get("confidence", 0.0)
        ev_refs = fc.get("supporting_evidence") or []
        try:
            conf_str = f"{float(conf):.2f}"
        except (TypeError, ValueError):
            conf_str = str(conf)
        print(
            f"    - [{status}] conf={conf_str}  evidence={len(ev_refs)}  "
            f"id={str(cid)[:8] if cid else '-'}"
        )
        print(f"        {statement}")


# ---------------------------------------------------------------------------
# token-cost rough estimate (chars/4 ~ tokens)
# ---------------------------------------------------------------------------


class _TokenMeter:
    def __init__(self) -> None:
        self.chars = 0
        self.events = 0

    def add_text(self, text: str) -> None:
        if not text:
            return
        self.chars += len(text)
        self.events += 1

    @property
    def tokens(self) -> int:
        return self.chars // 4


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


async def main(args: argparse.Namespace) -> int:
    configure_logging()

    total_stages = 9
    meter = _TokenMeter()

    # ---- 1. ingest -------------------------------------------------------
    _section(1, total_stages, f"ingest  rss={args.rss}  max={args.max_items}")
    cfg = {"kind": "rss", "feed_urls": [args.rss], "max_items": args.max_items}
    try:
        source_ids: list[str] = await _call(fetch_source, cfg)
    except Exception as exc:  # noqa: BLE001
        _err(f"fetch_source failed: {exc}")
        traceback.print_exc()
        return 2

    _ok(f"persisted {len(source_ids)} source(s)")
    for sid in source_ids:
        await _show_source(sid)
        async with session_scope() as session:
            row = await session.get(SourceModel, UUID(sid))
            if row is not None:
                meter.add_text(row.raw_text or "")
    if not source_ids:
        _warn("no new sources (everything was a dedup hit, or feed is empty) — exiting")
        return 0

    # ---- 2. extract ------------------------------------------------------
    _section(2, total_stages, "extract  per source")
    all_claim_ids: list[str] = []
    extract_failures = 0
    for sid in source_ids:
        try:
            claim_ids: list[str] = await _call(extract_claims, sid)
        except Exception as exc:  # noqa: BLE001
            _err(f"extract_claims({sid[:8]}) failed: {exc}")
            traceback.print_exc()
            extract_failures += 1
            continue
        print(f"    source {sid[:8]}: {len(claim_ids)} claim(s)")
        for cid in claim_ids:
            await _show_claim(cid)
        all_claim_ids.extend(claim_ids)

    if extract_failures and not all_claim_ids:
        _err("extraction produced nothing and hit failures — stopping")
        return 3
    if not all_claim_ids:
        _warn("no claims extracted — stopping")
        return 0
    _ok(f"extracted {len(all_claim_ids)} claim(s) total")

    # ---- 3. verify -------------------------------------------------------
    _section(3, total_stages, f"verify  cross-class adversarial  count={len(all_claim_ids)}")
    try:
        verify_result: dict[str, Any] = await _call(verify_claims, all_claim_ids)
    except Exception as exc:  # noqa: BLE001
        _err(f"verify_claims failed: {exc}")
        traceback.print_exc()
        return 4
    likely_true = int(verify_result.get("verified", 0))
    _ok(f"{likely_true}/{len(all_claim_ids)} likely_true")

    # ---- 4. index (best-effort) -----------------------------------------
    _section(4, total_stages, "index_evidence  (best-effort; Qdrant optional)")
    indexed = 0
    for sid in source_ids:
        try:
            res = await _call(index_evidence, sid)
            if res.get("skipped"):
                _warn(f"source {sid[:8]}: index skipped ({res})")
            else:
                indexed += int(res.get("indexed", 0))
                _ok(f"source {sid[:8]}: indexed={res.get('indexed', 0)}")
        except Exception as exc:  # noqa: BLE001
            _warn(f"index_evidence({sid[:8]}) failed (continuing): {exc}")
    if indexed:
        _ok(f"indexed {indexed} evidence chunks")

    if args.skip_discuss:
        print()
        _ok("--skip-discuss set; stopping after verify (baseline mode)")
        print(
            f"\n[done] sources={len(source_ids)}  claims={len(all_claim_ids)}  "
            f"verified={likely_true}  est_tokens~{meter.tokens}"
        )
        return 0

    # ---- 5. start_discussion --------------------------------------------
    _section(5, total_stages, f"start_discussion  topic={args.topic!r}  vertical={args.vertical}")
    try:
        discussion_id: str = await _call(start_discussion, args.topic, args.vertical, None)
    except Exception as exc:  # noqa: BLE001
        _err(f"start_discussion failed: {exc}")
        traceback.print_exc()
        return 5
    _ok(f"discussion_id={discussion_id}")
    meter.add_text(args.topic)

    # ---- 6. assemble_evidence_pack --------------------------------------
    _section(6, total_stages, "assemble_evidence_pack")
    try:
        pack_result: dict[str, Any] = await _call(assemble_evidence_pack, discussion_id)
    except Exception as exc:  # noqa: BLE001
        _err(f"assemble_evidence_pack failed: {exc}")
        traceback.print_exc()
        return 6
    pack_count = int(pack_result.get("evidence_count", 0))
    if pack_count == 0:
        _warn(
            "evidence pack is empty — discussion will run but personas will have "
            "nothing concrete to cite"
        )
    else:
        _ok(f"evidence_count={pack_count}")

    # ---- 7. run_discussion_graph ----------------------------------------
    _section(7, total_stages, "run_discussion_graph  (research + personas + critic + synth)")
    try:
        graph_result: dict[str, Any] = await _call(run_discussion_graph, discussion_id)
    except Exception as exc:  # noqa: BLE001
        _err(f"run_discussion_graph failed: {exc}")
        traceback.print_exc()
        return 7
    messages = graph_result.get("messages", []) or []
    final_claims = graph_result.get("final_claims", []) or []
    _ok(f"messages={len(messages)}  final_claims={len(final_claims)}")
    for msg in messages:
        agent = msg.get("agent_id", "unknown")
        role = msg.get("role", "assistant")
        content = (msg.get("content") or "")[:200]
        meter.add_text(msg.get("content") or "")
        suffix = "..." if len(msg.get("content") or "") > 200 else ""
        print(f"    - {_bold(str(agent))} [{role}]: {content}{suffix}")

    # ---- 8. persist_results ---------------------------------------------
    _section(8, total_stages, "persist_results")
    try:
        persist_out = await _call(persist_results, discussion_id, graph_result)
    except Exception as exc:  # noqa: BLE001
        _err(f"persist_results failed: {exc}")
        traceback.print_exc()
        return 8
    _ok(
        f"persisted messages={persist_out.get('messages', 0)}  "
        f"final_claims={persist_out.get('final_claims', 0)}"
    )

    # ---- 9. final claim ledger ------------------------------------------
    _section(9, total_stages, "final claim ledger")
    await _show_final_ledger(discussion_id, final_claims)

    # ---- summary --------------------------------------------------------
    print()
    print(
        _bold("[done]"),
        f"sources={len(source_ids)}  claims={len(all_claim_ids)}  "
        f"verified={likely_true}  messages={len(messages)}  "
        f"final={len(final_claims)}",
    )
    print(
        f"  rough cost estimate: ~{meter.tokens} tokens of LLM I/O "
        f"(chars/4 heuristic, undercount on output)"
    )
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Argus full Phase 4 demo runner (no Temporal needed)"
    )
    p.add_argument("--rss", required=True, help="RSS feed URL to ingest")
    p.add_argument(
        "--max-items",
        type=int,
        default=1,
        help="Max sources to ingest from the feed (default 1)",
    )
    p.add_argument(
        "--topic",
        required=True,
        help="Discussion topic / question for the multi-agent debate",
    )
    p.add_argument(
        "--vertical",
        default="geopolitics",
        help="Vertical name (default: geopolitics)",
    )
    p.add_argument(
        "--skip-discuss",
        action="store_true",
        help="Stop after verify; behaves like scripts/run_baseline.py",
    )
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(parse_args())))
