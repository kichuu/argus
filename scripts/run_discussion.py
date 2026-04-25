"""End-to-end CLI runner for the Argus discussion pipeline.

Two modes:
- --mock (default if OPENAI_API_KEY is unset): canned LLM responses, gold-backed
  evidence. Lets devs exercise the wiring without burning tokens.
- --live: real OpenAIProvider plus a LocalGoldRetriever (Qdrant out of scope here).

Run:
    uv run python -m scripts.run_discussion --mock
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from argus_agents import CouncilOrchestrator
from argus_core.logging import configure_logging, get_logger
from argus_core.personas import load_persona_library
from argus_core.settings import get_settings

from scripts._mock_provider import (
    LocalGoldRetriever,
    MockProvider,
)

if TYPE_CHECKING:
    from argus_agents.state import DiscussionState
    from argus_extraction.providers.base import Provider

logger = get_logger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_discussion.py")
    parser.add_argument(
        "--topic",
        default="What did the FOMC decide on December 18, 2024?",
    )
    parser.add_argument("--vertical", default="finance")
    parser.add_argument("--personas", type=int, default=3)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true", help="use canned LLM responses")
    mode.add_argument("--live", action="store_true", help="hit the real OpenAI API")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _resolve_mode(args: argparse.Namespace) -> str:
    if args.live and args.mock:
        raise SystemExit("--mock and --live are mutually exclusive")
    if args.live:
        return "live"
    if args.mock:
        return "mock"
    return "mock" if not os.environ.get("OPENAI_API_KEY") else "live"


def _gold_path() -> Path:
    settings = get_settings()
    candidate = settings.gold_set_path
    if candidate.is_absolute():
        return candidate
    repo_root = Path(__file__).resolve().parent.parent
    return (repo_root / candidate).resolve()


def _build_orch_mock(vertical: str) -> CouncilOrchestrator:
    retriever = LocalGoldRetriever(_gold_path(), vertical)
    provider: Provider = MockProvider()
    return CouncilOrchestrator(
        provider=provider,
        retriever=retriever,
        library=load_persona_library(),
        extractor_family="gpt",
    )


def _build_orch_live(vertical: str) -> CouncilOrchestrator:
    from argus_extraction.providers import OpenAIProvider, family_of

    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("--live requested but OPENAI_API_KEY is not set")
    retriever = LocalGoldRetriever(_gold_path(), vertical)
    provider = OpenAIProvider()
    return CouncilOrchestrator(
        provider=provider,
        retriever=retriever,
        library=load_persona_library(),
        extractor_family=family_of(settings.default_extractor_model),
    )


def _print_summary(state: DiscussionState, mode: str) -> None:
    print(f"=== discussion complete (mode={mode}) ===")
    print(f"topic:          {state.topic}")
    print(f"discussion_id:  {state.discussion_id}")
    print(f"evidence_count: {len(state.evidence_pack.evidence)}")
    print(f"persona_count:  {len(state.personas)}")
    print(f"message_count:  {len(state.messages)}")
    print(f"claim_count:    {len(state.final_claims)}")
    if state.errors:
        print(f"errors:         {len(state.errors)}")
        for err in state.errors:
            print(f"  - {err}")
    print()
    if not state.final_claims:
        print("(no claims produced)")
        return
    for i, claim in enumerate(state.final_claims, 1):
        print(
            f"[{i}] {claim.id}\n"
            f"    statement:   {claim.statement}\n"
            f"    status:      {claim.status.value}\n"
            f"    confidence:  {claim.confidence:.2f}\n"
            f"    supporting:  {len(claim.supporting_evidence)}\n"
        )


def _write_output(state: DiscussionState, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    print(f"wrote full state to {output}")


async def _run(args: argparse.Namespace) -> int:
    if args.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
    configure_logging()

    mode = _resolve_mode(args)
    logger.info(
        "run_discussion_start",
        mode=mode,
        topic=args.topic,
        vertical=args.vertical,
        personas=args.personas,
    )

    orch = (
        _build_orch_mock(args.vertical)
        if mode == "mock"
        else _build_orch_live(args.vertical)
    )

    state = await orch.run(args.topic, vertical=args.vertical, num_personas=args.personas)
    _print_summary(state, mode)
    if args.output is not None:
        _write_output(state, args.output)
    return 0 if state.final_claims else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
