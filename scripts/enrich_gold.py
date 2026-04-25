"""Enrich Argus gold-set items with real article text and verbatim-span offsets.

The gold set in ``eval/gold.jsonl`` measures citation precision/recall for the
extractor. Each item has an ``expected_verbatim_span`` (the substring the
extractor is expected to cite) and ``expected_char_start`` /
``expected_char_end`` offsets that the runner uses for span-level scoring.

Until offsets are filled in and ``verified=true``, citation_precision is
always 0 (the metric requires non-null offsets). This script enriches items
in place: it fetches the source URL, strips HTML, locates the verbatim span,
and writes the resolved offsets and cleaned text back to the JSONL file.

Usage
-----
    uv run python scripts/enrich_gold.py [--gold ./eval/gold.jsonl]
                                         [--dry-run] [--only-id ID]

Adding a new gold item
----------------------
1. Append a new line to ``eval/gold.jsonl`` matching ``GoldClaim`` (see
   ``eval/gold_schema.py``).
2. Use a real, publicly-fetchable URL for ``source_url`` (preferred: tier-1
   primaries -- reuters.com, apnews.com, gov.uk, un.org, treasury.gov, etc.).
3. Set ``expected_verbatim_span`` to a literal substring you expect the
   extractor to cite. Pick a span that is unambiguous and self-contained
   (don't span across paragraphs).
4. Leave ``expected_char_start``/``expected_char_end`` as ``null`` and
   ``verified`` as ``false``.
5. Run ``uv run python scripts/enrich_gold.py --only-id <new-id>``. The
   script will fetch the URL, locate the span, and fill in the offsets.

Verbatim-span policy
--------------------
The extractor is expected to emit a *literal substring* of the cleaned source
text. After enrichment the gold ``expected_verbatim_span`` is rewritten to
the exact substring at the resolved offsets so the verifier scores against
the canonical form. Whitespace in the source is collapsed to single spaces
the same way ``argus_ingestion.base.normalize_text`` does it -- this is the
same shape extracted text will have at runtime.

Why placeholder URLs are skipped
--------------------------------
The current 10 items use ``https://example.invalid/...`` placeholder URLs.
The script will NOT try to fetch them and will NOT guess the canonical URL.
Fabricating a URL would silently couple the gold set to whatever document
the script happened to pick, defeating the point of a hand-labelled
benchmark. The user must replace placeholders with real URLs before
enrichment can run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

PLACEHOLDER_PREFIX = "https://example.invalid/"
USER_AGENT = "argus-eval/0.1 (+mailto:vishnuvisa00@gmail.com)"
HTTP_TIMEOUT = 10.0
FUZZY_THRESHOLD = 0.85

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class EnrichResult:
    item_id: str
    status: str  # "enriched" | "placeholder" | "not_found" | "error" | "already_verified"
    detail: str = ""
    char_start: int | None = None
    char_end: int | None = None
    resolved_span: str | None = None


def _clean_text(html: str) -> str:
    """HTML -> whitespace-collapsed plain text. Mirrors
    ``argus_ingestion.base.normalize_text``."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    # Drop script/style/nav/footer noise so the span search is on article text.
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()
    stripped = soup.get_text(separator=" ")
    return _WHITESPACE_RE.sub(" ", stripped).strip()


def _normalize_span(span: str) -> str:
    return _WHITESPACE_RE.sub(" ", span).strip()


def _fuzzy_locate(span: str, text: str, threshold: float = FUZZY_THRESHOLD) -> tuple[int, int, float] | None:
    """Sliding-window fuzzy match. Returns (start, end, ratio) or None."""
    if not span or not text:
        return None
    n = len(span)
    if n > len(text):
        return None
    best_ratio = 0.0
    best_start = -1
    # Step ~= 25% of span length for speed; small spans step by 1.
    step = max(1, n // 4)
    matcher = SequenceMatcher(autojunk=False)
    matcher.set_seq2(span)
    for start in range(0, len(text) - n + 1, step):
        window = text[start : start + n]
        matcher.set_seq1(window)
        ratio = matcher.real_quick_ratio()
        if ratio < threshold:
            continue
        ratio = matcher.ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start
            if ratio >= 0.99:
                break
    if best_start < 0 or best_ratio < threshold:
        return None
    # Refine: search +/- step around the best window for a tighter alignment.
    refine_lo = max(0, best_start - step)
    refine_hi = min(len(text) - n, best_start + step)
    for start in range(refine_lo, refine_hi + 1):
        window = text[start : start + n]
        matcher.set_seq1(window)
        ratio = matcher.ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = start
    return (best_start, best_start + n, best_ratio)


def _fetch(url: str) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _enrich_one(item: dict[str, Any]) -> tuple[EnrichResult, str | None]:
    """Returns (result, cleaned_text). cleaned_text is None when not fetched."""
    item_id = str(item.get("id", "?"))

    if item.get("verified") is True:
        return (
            EnrichResult(item_id, "already_verified", detail="verified=true; skipping"),
            None,
        )

    source_url = str(item.get("source_url", ""))
    if source_url.startswith(PLACEHOLDER_PREFIX):
        return (
            EnrichResult(
                item_id,
                "placeholder",
                detail="placeholder URL -- needs manual replacement before enrichment",
            ),
            None,
        )

    try:
        html = _fetch(source_url)
    except Exception as exc:
        return (
            EnrichResult(item_id, "error", detail=f"fetch failed: {type(exc).__name__}: {exc}"),
            None,
        )

    cleaned = _clean_text(html)
    if not cleaned:
        return EnrichResult(item_id, "error", detail="cleaned text was empty"), None

    raw_span = str(item.get("expected_verbatim_span", ""))
    span = _normalize_span(raw_span)
    if not span:
        return EnrichResult(item_id, "error", detail="expected_verbatim_span is empty"), cleaned

    # 1) exact match on the normalized cleaned text.
    start = cleaned.find(span)
    if start >= 0:
        end = start + len(span)
        resolved = cleaned[start:end]
        return (
            EnrichResult(item_id, "enriched", detail="exact match", char_start=start,
                         char_end=end, resolved_span=resolved),
            cleaned,
        )

    # 2) fuzzy fallback.
    hit = _fuzzy_locate(span, cleaned)
    if hit is None:
        return (
            EnrichResult(
                item_id,
                "not_found",
                detail=f"verbatim span not found in cleaned article text ({len(cleaned)} chars)",
            ),
            cleaned,
        )
    s, e, ratio = hit
    resolved = cleaned[s:e]
    return (
        EnrichResult(
            item_id,
            "enriched",
            detail=f"fuzzy match ratio={ratio:.3f}",
            char_start=s,
            char_end=e,
            resolved_span=resolved,
        ),
        cleaned,
    )


def _load_items(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                items.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON at {path}:{line_no}: {exc}") from exc
    return items


def _write_items(path: Path, items: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _apply_result(item: dict[str, Any], result: EnrichResult, source_text: str) -> None:
    """Mutate item in place with enrichment results."""
    item["expected_char_start"] = result.char_start
    item["expected_char_end"] = result.char_end
    if result.resolved_span is not None:
        item["expected_verbatim_span"] = result.resolved_span
    item["source_text"] = source_text
    item["verified"] = True
    today = date.today().isoformat()
    note = f"auto-enriched from {item.get('source_url')} on {today}"
    existing = str(item.get("labeler_notes", "")).strip()
    item["labeler_notes"] = f"{existing} | {note}".strip(" |") if existing else note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="enrich_gold")
    parser.add_argument("--gold", type=Path, default=Path("./eval/gold.jsonl"))
    parser.add_argument("--dry-run", action="store_true",
                        help="show intended changes without writing the file")
    parser.add_argument("--only-id", type=str, default=None,
                        help="enrich only the item with this id")
    args = parser.parse_args(argv)

    if not args.gold.exists():
        print(f"error: gold file not found: {args.gold}", file=sys.stderr)
        return 2

    items = _load_items(args.gold)
    if not items:
        print(f"error: no items in {args.gold}", file=sys.stderr)
        return 2

    counts = {"enriched": 0, "skipped_placeholder": 0, "not_found": 0,
              "errors": 0, "already_verified": 0}
    placeholder_ids: list[str] = []
    not_found_ids: list[str] = []
    error_lines: list[str] = []

    for item in items:
        item_id = str(item.get("id", "?"))
        if args.only_id and item_id != args.only_id:
            continue

        result, cleaned = _enrich_one(item)

        if result.status == "enriched":
            counts["enriched"] += 1
            assert cleaned is not None  # by construction in _enrich_one
            if args.dry_run:
                print(f"[DRY   ] {item_id}: would enrich -> "
                      f"start={result.char_start} end={result.char_end} "
                      f"({result.detail}); source_text would be {len(cleaned)} chars")
            else:
                _apply_result(item, result, cleaned)
                print(f"[ENRICH] {item_id}: start={result.char_start} "
                      f"end={result.char_end} ({result.detail})")
        elif result.status == "placeholder":
            counts["skipped_placeholder"] += 1
            placeholder_ids.append(item_id)
            print(f"[SKIP  ] {item_id}: {result.detail}")
        elif result.status == "not_found":
            counts["not_found"] += 1
            not_found_ids.append(item_id)
            print(f"[MISS  ] {item_id}: {result.detail}")
        elif result.status == "already_verified":
            counts["already_verified"] += 1
            print(f"[VERIFD] {item_id}: {result.detail}")
        else:
            counts["errors"] += 1
            error_lines.append(f"  {item_id}: {result.detail}")
            print(f"[ERROR ] {item_id}: {result.detail}")

    if not args.dry_run and counts["enriched"] > 0:
        _write_items(args.gold, items)
        print(f"\nWrote enriched gold set back to {args.gold}")
    elif args.dry_run:
        print("\n(dry run -- no changes written)")

    print("\n=== summary ===")
    print(f"enriched:            {counts['enriched']}")
    print(f"skipped_placeholder: {counts['skipped_placeholder']}")
    print(f"not_found:           {counts['not_found']}")
    print(f"errors:              {counts['errors']}")
    print(f"already_verified:    {counts['already_verified']}")

    if placeholder_ids:
        print("\nItems still using https://example.invalid/ placeholder URLs "
              "(replace with real publisher URLs to enable enrichment):")
        for pid in placeholder_ids:
            print(f"  - {pid}")

    if not_found_ids:
        print("\nItems where the verbatim span was not found in the fetched "
              "article (review span text or URL):")
        for nid in not_found_ids:
            print(f"  - {nid}")

    if error_lines:
        print("\nErrors:")
        for line in error_lines:
            print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
