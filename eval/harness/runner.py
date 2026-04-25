from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from eval.harness.citation_precision import evaluate_extraction, load_gold

try:
    from argus_core.schemas import Source  # type: ignore
    from argus_core.settings import get_settings  # type: ignore
    from argus_extraction.extractor import ClaimExtractor  # type: ignore
    from argus_extraction.providers import get_provider  # type: ignore
    from argus_extraction.verifier import verify_extraction  # type: ignore
    from argus_ingestion.base import compute_content_hash  # type: ignore
except Exception:  # pragma: no cover - optional deps may be missing in tests
    ClaimExtractor = None  # type: ignore[assignment]
    Source = None  # type: ignore[assignment]
    get_settings = None  # type: ignore[assignment]
    get_provider = None  # type: ignore[assignment]
    verify_extraction = None  # type: ignore[assignment]
    compute_content_hash = None  # type: ignore[assignment]


def _print_table(metrics: dict[str, float | int]) -> None:
    rows = [
        ("citation_precision", metrics["citation_precision"]),
        ("citation_recall", metrics["citation_recall"]),
        ("exact_match_rate", metrics["exact_match_rate"]),
        ("hallucination_rate", metrics["hallucination_rate"]),
        ("n_gold", metrics["n_gold"]),
        ("n_extracted", metrics["n_extracted"]),
    ]
    width = max(len(name) for name, _ in rows)
    print(f"{'metric'.ljust(width)} | value")
    print(f"{'-' * width}-+-{'-' * 10}")
    for name, value in rows:
        if isinstance(value, float):
            print(f"{name.ljust(width)} | {value:.4f}")
        else:
            print(f"{name.ljust(width)} | {value}")


def _claim_to_dict(claim: Any, gold_id: str) -> dict[str, Any]:
    """Coerce an ExtractedClaim (or compatible) into the dict shape that
    `evaluate_extraction` expects: id, statement, verbatim_span,
    char_start, char_end."""
    if isinstance(claim, dict):
        d = dict(claim)
    elif hasattr(claim, "model_dump"):
        d = claim.model_dump()
    else:
        d = dict(claim)
    # Tag with the gold item id so the matcher can join by id without
    # relying on fuzzy string matching alone.
    d.setdefault("id", gold_id)
    return d


async def _run_extraction_async(gold_items: list[Any]) -> list[dict[str, Any]]:
    if (
        ClaimExtractor is None
        or Source is None
        or get_provider is None
        or verify_extraction is None
        or compute_content_hash is None
        or get_settings is None
    ):
        print(
            "TODO: argus_extraction / argus_core / argus_ingestion not importable; "
            "skipping extraction step.",
            file=sys.stderr,
        )
        return []

    settings = get_settings()
    if not getattr(settings, "openai_api_key", ""):
        print(
            "OPENAI_API_KEY not set; skipping extraction step. "
            "Set OPENAI_API_KEY to run the extractor against the gold set.",
            file=sys.stderr,
        )
        return []

    try:
        provider = get_provider("openai")
    except Exception as exc:
        print(f"failed to construct OpenAI provider: {exc}", file=sys.stderr)
        return []

    extractor = ClaimExtractor(provider=provider)
    results: list[dict[str, Any]] = []

    for g in gold_items:
        try:
            source = Source(
                url=g.source_url if g.source_url.startswith("http") else None,
                title=g.id,
                content_hash=compute_content_hash(g.source_text),
                raw_text=g.source_text,
                trust_tier=g.trust_tier or 4,
                publisher=g.publisher,
            )
        except Exception as exc:
            print(f"could not build Source for {g.id}: {exc}", file=sys.stderr)
            continue

        try:
            raw_result = await extractor.extract(source)
        except Exception as exc:
            print(f"extraction failed for {g.id}: {exc}", file=sys.stderr)
            continue

        try:
            verified, errs = verify_extraction(source, raw_result)
        except Exception as exc:
            print(f"verification failed for {g.id}: {exc}", file=sys.stderr)
            continue

        if errs:
            print(
                f"{g.id}: {len(errs)} span(s) dropped during verification",
                file=sys.stderr,
            )

        for c in verified.claims:
            results.append(_claim_to_dict(c, g.id))

    return results


async def _amain(args: argparse.Namespace) -> int:
    gold = load_gold(args.gold)
    if not gold:
        print(
            "No gold claims found. Label items in eval/gold.jsonl using "
            "the GoldClaim schema."
        )
        return 0

    extracted = await _run_extraction_async(gold)
    metrics = evaluate_extraction(gold, extracted)
    _print_table(metrics)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nWrote results to {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval.harness.runner")
    parser.add_argument("--gold", type=Path, default=Path("./eval/gold.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("./eval/results.json"))
    args = parser.parse_args(argv)

    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
