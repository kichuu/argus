from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from eval.gold_schema import GoldClaim

CHAR_TOLERANCE = 5
FUZZY_THRESHOLD = 0.85


def load_gold(path: Path) -> list[GoldClaim]:
    if not path.exists():
        return []
    items: list[GoldClaim] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            items.append(GoldClaim.model_validate(obj))
    return items


def _spans_match(
    g_start: int | None, g_end: int | None, e_start: int | None, e_end: int | None
) -> bool:
    if g_start is None or g_end is None or e_start is None or e_end is None:
        return False
    return abs(e_start - g_start) <= CHAR_TOLERANCE and abs(e_end - g_end) <= CHAR_TOLERANCE


def _find_match(gold: GoldClaim, extracted: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in extracted:
        if str(item.get("id", "")) == gold.id:
            return item
    best: dict[str, Any] | None = None
    best_ratio = 0.0
    for item in extracted:
        statement = str(item.get("statement", ""))
        if not statement:
            continue
        ratio = SequenceMatcher(None, statement, gold.statement).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = item
    if best_ratio >= FUZZY_THRESHOLD:
        return best
    return None


def _extract_span(item: dict[str, Any]) -> tuple[str | None, int | None, int | None]:
    span = item.get("verbatim_span") or item.get("expected_verbatim_span")
    start = item.get("char_start", item.get("expected_char_start"))
    end = item.get("char_end", item.get("expected_char_end"))
    return (
        str(span) if span is not None else None,
        int(start) if start is not None else None,
        int(end) if end is not None else None,
    )


def evaluate_extraction(
    gold: list[GoldClaim], extracted: list[dict[str, Any]]
) -> dict[str, float | int]:
    n_gold = len(gold)
    n_extracted = len(extracted)

    if n_gold == 0 and n_extracted == 0:
        return {
            "citation_precision": 0.0,
            "citation_recall": 0.0,
            "exact_match_rate": 0.0,
            "hallucination_rate": 0.0,
            "n_gold": 0,
            "n_extracted": 0,
        }

    gold_by_id: dict[str, GoldClaim] = {g.id: g for g in gold}
    matched_gold_ids: set[str] = set()
    precision_hits = 0
    exact_hits = 0
    hallucinations = 0

    for item in extracted:
        span_text, e_start, e_end = _extract_span(item)
        gold_match: GoldClaim | None = None
        item_id = str(item.get("id", ""))
        if item_id and item_id in gold_by_id:
            gold_match = gold_by_id[item_id]
        else:
            best_ratio = 0.0
            statement = str(item.get("statement", ""))
            for g in gold:
                if not statement:
                    break
                ratio = SequenceMatcher(None, statement, g.statement).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    gold_match = g
            if best_ratio < FUZZY_THRESHOLD:
                gold_match = None

        if gold_match is not None:
            matched_gold_ids.add(gold_match.id)
            if _spans_match(
                gold_match.expected_char_start,
                gold_match.expected_char_end,
                e_start,
                e_end,
            ):
                precision_hits += 1
            if span_text is not None and span_text == gold_match.expected_verbatim_span:
                exact_hits += 1
            if span_text is not None and span_text not in gold_match.source_text:
                hallucinations += 1
        else:
            if span_text is None:
                hallucinations += 1

    citation_precision = precision_hits / n_extracted if n_extracted else 0.0
    citation_recall = len(matched_gold_ids) / n_gold if n_gold else 0.0
    exact_match_rate = exact_hits / n_gold if n_gold else 0.0
    hallucination_rate = hallucinations / n_extracted if n_extracted else 0.0

    return {
        "citation_precision": citation_precision,
        "citation_recall": citation_recall,
        "exact_match_rate": exact_match_rate,
        "hallucination_rate": hallucination_rate,
        "n_gold": n_gold,
        "n_extracted": n_extracted,
    }


def find_match_for_gold(
    gold: GoldClaim, extracted: list[dict[str, Any]]
) -> dict[str, Any] | None:
    return _find_match(gold, extracted)
