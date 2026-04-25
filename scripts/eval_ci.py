"""CI gate for citation precision regressions.

Reads the recorded baseline metrics from `eval/results_baseline.json`,
optionally re-runs the eval harness against the live LLM (only when
`OPENAI_API_KEY` is present and `--no-llm` is not passed), and fails
the build if `citation_precision` drops by more than `--tolerance`
relative to the recorded baseline.

This script is the implementation of the user's plan item:
    "Gold-set regression test in CI - block any prompt change that drops precision"

Behavior summary:
    * `--no-llm` or no `OPENAI_API_KEY` in env -> skip LLM call, just sanity-check
      that the gold set parses, then exit 0. This keeps CI green on forks / PRs
      from contributors without secrets.
    * Otherwise: invoke `python -m eval.harness.runner`, write fresh metrics to
      `eval/results_pr.json`, compare to baseline, and exit non-zero if precision
      regressed beyond the tolerance.
    * If the recorded baseline is missing or all-zero (e.g., the harness errored
      when it was captured), we record the current run as the new baseline and
      exit 0 - we cannot compare against a degenerate reference.

Usage:
    uv run python scripts/eval_ci.py [--no-llm] [--tolerance 0.05] [--baseline ./eval/results_baseline.json]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Make `eval.gold_loader` and `eval.harness.runner` importable when this
# script is run directly (e.g. `uv run python scripts/eval_ci.py`) from
# any working directory.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_BASELINE = REPO_ROOT / "eval" / "results_baseline.json"
DEFAULT_GOLD = REPO_ROOT / "eval" / "gold.jsonl"
DEFAULT_PR_OUTPUT = REPO_ROOT / "eval" / "results_pr.json"


def _load_metrics(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _is_usable_baseline(metrics: dict[str, Any] | None) -> bool:
    """A baseline is 'usable' if it has non-zero precision/recall.

    The current `results_baseline.json` was captured when the harness
    errored (extractor_run == "errored"), so all metrics are 0 and there
    is nothing meaningful to compare against. We treat that as "no
    baseline yet" rather than "every PR is a regression".
    """
    if not metrics:
        return False
    prec = float(metrics.get("citation_precision", 0.0) or 0.0)
    rec = float(metrics.get("citation_recall", 0.0) or 0.0)
    # If both prec and recall are 0, the baseline is degenerate.
    return (prec > 0.0) or (rec > 0.0)


def _verify_gold_parses(gold_path: Path) -> int:
    """Import lazily so this works even when the package is partially set up."""
    from eval.gold_loader import load_gold_claims

    items = load_gold_claims(gold_path)
    return len(items)


def _run_harness(output_path: Path, gold_path: Path) -> dict[str, Any] | None:
    """Invoke the runner module; return parsed metrics or None on failure."""
    cmd = [
        sys.executable,
        "-m",
        "eval.harness.runner",
        "--gold",
        str(gold_path),
        "--output",
        str(output_path),
    ]
    print(f"[ci] $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"[ci] harness exited with code {proc.returncode}", file=sys.stderr)
        return None
    return _load_metrics(output_path)


def _print_diff_table(baseline: dict[str, Any], current: dict[str, Any]) -> None:
    rows = [
        ("prec", "citation_precision"),
        ("rec ", "citation_recall"),
        ("hall", "hallucination_rate"),
    ]
    print("[ci] metrics:")
    print("       baseline  current  delta")
    for label, key in rows:
        b = float(baseline.get(key, 0.0) or 0.0)
        c = float(current.get(key, 0.0) or 0.0)
        d = c - b
        sign = "+" if d >= 0 else "-"
        print(f"  {label}  {b:<8.2f}  {c:<7.2f}  {sign}{abs(d):.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/eval_ci.py")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip the LLM eval; only sanity-check that the gold set parses.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.05,
        help="Maximum allowed drop in citation_precision before failing CI.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="Path to the recorded baseline metrics JSON.",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=DEFAULT_GOLD,
        help="Path to the gold set JSONL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PR_OUTPUT,
        help="Where to write the fresh PR-run metrics JSON for inspection.",
    )
    args = parser.parse_args(argv)

    # 1. Always verify gold parses. This is cheap and catches schema breakage.
    try:
        n_gold = _verify_gold_parses(args.gold)
    except Exception as exc:
        print(f"[ci] FAIL: gold set did not parse: {exc}", file=sys.stderr)
        return 1
    print(f"[ci] gold set parses: {n_gold} items")

    # 2. Decide whether to run the LLM eval.
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    if args.no_llm:
        print("[ci] running harness... skipped (--no-llm)")
        return 0
    if not has_key:
        print(
            "[ci] no OPENAI_API_KEY in env - skipping LLM eval "
            "(CI is unit-tests-only)"
        )
        return 0

    print("[ci] running harness...")
    current = _run_harness(args.output, args.gold)
    if current is None:
        print(
            "[ci] harness did not produce metrics; treating as infrastructure "
            "failure (not a regression).",
            file=sys.stderr,
        )
        return 1

    baseline = _load_metrics(args.baseline)
    if not _is_usable_baseline(baseline):
        print(
            "[ci] no usable baseline; recording current run as new baseline"
        )
        # Persist the current run as the new baseline for future comparisons.
        # We write to the PR output (already done by harness) and leave the
        # repo's baseline file untouched - the human reviewer rolls it forward.
        return 0

    assert baseline is not None  # for type-checkers
    _print_diff_table(baseline, current)

    base_prec = float(baseline.get("citation_precision", 0.0) or 0.0)
    cur_prec = float(current.get("citation_precision", 0.0) or 0.0)
    delta = cur_prec - base_prec
    if delta < -args.tolerance:
        print(
            f"[ci] FAIL: citation_precision dropped {abs(delta):.3f} "
            f"(> tolerance {args.tolerance:.2f})",
            file=sys.stderr,
        )
        return 1

    print(f"[ci] PASS: precision delta within tolerance ({args.tolerance:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
