"""Run the Phase 4 baseline (fetch -> extract -> verify) directly, without Temporal.

The Temporal worker calls these same activities; this script invokes the underlying
async functions, so you can exercise the pipeline against a real RSS feed without
running `temporal server start-dev`.

Usage:
    uv run python scripts/run_baseline.py --rss https://feeds.reuters.com/reuters/worldNews --max-items 2
    uv run python scripts/run_baseline.py --rss https://feeds.bbci.co.uk/news/world/rss.xml --max-items 1
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

from argus_core.db.models import ClaimModel, SourceModel
from argus_core.db.session import session_scope
from argus_core.logging import configure_logging
from argus_workers.activities.extract import extract_claims
from argus_workers.activities.fetch import fetch_source
from argus_workers.activities.verify import verify_claims


async def _show_source(source_id: str) -> None:
    async with session_scope() as session:
        row = await session.get(SourceModel, UUID(source_id))
        if row is None:
            return
        print(f"  source {source_id[:8]}  trust={row.trust_tier}  publisher={row.publisher!r}")
        print(f"    title:  {row.title[:80]}")
        print(f"    chars:  {len(row.raw_text)}")


async def _show_claim(claim_id: str) -> None:
    async with session_scope() as session:
        row = await session.get(ClaimModel, UUID(claim_id))
        if row is None:
            return
        ev = row.supporting_evidence[0] if row.supporting_evidence else {}
        span = ev.get("verbatim_span", "")[:100]
        print(
            f"    claim {claim_id[:8]}  status={row.status}  conf={row.confidence:.2f}"
        )
        print(f"      statement: {row.statement[:100]}")
        if span:
            print(f"      span:      {span!r}")


async def main(rss_url: str, max_items: int) -> int:
    configure_logging()

    print(f"\n[1/3] fetch  rss={rss_url}  max={max_items}")
    cfg = {"kind": "rss", "feed_urls": [rss_url], "max_items": max_items}
    try:
        source_ids = await fetch_source.__wrapped__(cfg)  # type: ignore[attr-defined]
    except AttributeError:
        # Some temporalio versions don't expose __wrapped__
        source_ids = await fetch_source(cfg)
    print(f"      persisted {len(source_ids)} sources")
    for sid in source_ids:
        await _show_source(sid)
    if not source_ids:
        print("      nothing to extract — exiting")
        return 0

    print(f"\n[2/3] extract  per source")
    all_claims: list[str] = []
    for sid in source_ids:
        try:
            claim_ids = await extract_claims.__wrapped__(sid)  # type: ignore[attr-defined]
        except AttributeError:
            claim_ids = await extract_claims(sid)
        print(f"  source {sid[:8]}: {len(claim_ids)} claims")
        for cid in claim_ids:
            await _show_claim(cid)
        all_claims.extend(claim_ids)
    if not all_claims:
        print("      no claims extracted — exiting")
        return 0

    print(f"\n[3/3] verify  cross-class adversarial verifier  count={len(all_claims)}")
    try:
        result = await verify_claims.__wrapped__(all_claims)  # type: ignore[attr-defined]
    except AttributeError:
        result = await verify_claims(all_claims)
    print(f"      {result['verified']}/{len(all_claims)} likely_true")

    print(f"\n[done] sources={len(source_ids)}  claims={len(all_claims)}  verified={result['verified']}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 4 baseline runner (no Temporal)")
    p.add_argument("--rss", required=True, help="RSS feed URL to fetch")
    p.add_argument("--max-items", type=int, default=2, help="Max sources to ingest (default 2)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(asyncio.run(main(args.rss, args.max_items)))
