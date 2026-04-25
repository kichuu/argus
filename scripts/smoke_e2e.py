"""End-to-end smoke test for the Argus orchestrator.

Single-process: no DB, no Redis, no Temporal, no real OpenAI calls. Builds
a CouncilOrchestrator with a MockProvider + LocalGoldRetriever and runs
one discussion through it, asserting the phase sequence, that callbacks
fire for personas + claims, and that final_claims is non-empty.

Use this as a sanity gate before any infrastructural change ships:

    uv run python -m scripts.smoke_e2e
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from argus_agents import CouncilOrchestrator
from argus_core.logging import configure_logging, get_logger
from argus_core.personas import load_persona_library

from scripts._mock_provider import LocalGoldRetriever, MockProvider

logger = get_logger(__name__)


_EXPECTED_PHASES = (
    "researching",
    "planning",
    "debating",
    "criticizing",
    "synthesizing",
    "completed",
)


def _gold_path() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "eval" / "gold.jsonl"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="smoke_e2e.py")
    parser.add_argument("--vertical", default="finance")
    parser.add_argument(
        "--topic",
        default="What did the FOMC decide on December 18, 2024?",
    )
    parser.add_argument("--num-personas", type=int, default=3)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    if args.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
    configure_logging()

    phases: list[str] = []
    posts: list[Any] = []
    claims: list[Any] = []
    statuses: list[tuple[str, str]] = []

    async def on_phase(phase: str) -> None:
        phases.append(phase)

    async def on_post(msg: Any) -> None:
        posts.append(msg)

    async def on_status(agent_id: str, state: str, _extra: dict) -> None:
        statuses.append((agent_id, state))

    async def on_claim(claim: Any) -> None:
        claims.append(claim)

    orch = CouncilOrchestrator(
        provider=MockProvider(),
        retriever=LocalGoldRetriever(_gold_path(), args.vertical),
        library=load_persona_library(),
        on_post=on_post,
        on_status=on_status,
        on_phase=on_phase,
        on_claim=on_claim,
        extractor_family="gpt",
    )
    state = await orch.run(
        args.topic,
        vertical=args.vertical,
        num_personas=args.num_personas,
    )

    failures: list[str] = []
    for expected in _EXPECTED_PHASES:
        if expected not in phases:
            failures.append(f"missing phase {expected!r} in {phases}")
    persona_post_count = sum(1 for m in posts if str(m.role).endswith("persona"))
    if persona_post_count < args.num_personas:
        failures.append(
            f"expected >= {args.num_personas} persona posts, got {persona_post_count}"
        )
    if not claims:
        failures.append("no claim events emitted")
    if not state.final_claims:
        failures.append("state.final_claims is empty")

    print("=== smoke_e2e summary ===")
    print(f"topic:          {args.topic}")
    print(f"vertical:       {args.vertical}")
    print(f"phases:         {phases}")
    print(f"persona posts:  {persona_post_count}")
    print(f"total messages: {len(posts)}")
    print(f"claims:         {len(claims)}")
    print(f"final_claims:   {len(state.final_claims)}")
    print(f"errors:         {len(state.errors)}")
    for err in state.errors:
        print(f"  - {err}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
