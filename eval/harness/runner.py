from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from eval.harness.citation_precision import evaluate_extraction, load_gold

try:
    from argus_extraction.extractor import ClaimExtractor  # type: ignore
except Exception:
    ClaimExtractor = None  # type: ignore[assignment]


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


def _run_extraction(gold_items: list[Any]) -> list[dict[str, Any]]:
    if ClaimExtractor is None:
        print(
            "TODO: argus_extraction.ClaimExtractor not importable yet; "
            "skipping extraction step.",
            file=sys.stderr,
        )
        return []
    extractor = ClaimExtractor()
    results: list[dict[str, Any]] = []
    for g in gold_items:
        try:
            extracted = extractor.extract(g.source_text, source_url=g.source_url)
        except Exception as exc:
            print(f"extraction failed for {g.id}: {exc}", file=sys.stderr)
            continue
        for c in extracted:
            if isinstance(c, dict):
                results.append(c)
            else:
                results.append(
                    c.model_dump() if hasattr(c, "model_dump") else dict(c)
                )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval.harness.runner")
    parser.add_argument("--gold", type=Path, default=Path("./eval/gold.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("./eval/results.json"))
    args = parser.parse_args(argv)

    gold = load_gold(args.gold)
    if not gold:
        print(
            "No gold claims found. Label items in eval/gold.jsonl using "
            "the GoldClaim schema."
        )
        return 0

    extracted = _run_extraction(gold)
    metrics = evaluate_extraction(gold, extracted)
    _print_table(metrics)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nWrote results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
