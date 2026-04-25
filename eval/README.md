# Argus eval — gold set + harness

This directory contains the gold-labeled benchmark used to gate every prompt and
pipeline change in Argus. **Without it the eval is vibes.** The user's plan calls
this out as the most important artifact in Phase 0.

## What's here

- `gold_schema.py` — `GoldClaim` Pydantic schema (extended for vertical metadata)
- `gold.jsonl` — hand-labeled benchmark items (one per line)
- `gold_loader.py` — strict loader that raises on the first malformed item
- `harness/` — runner + citation-precision metrics
- `tests/` — schema/loader regression tests

## Vertical

`config/vertical.yaml` declares **geopolitics** as the active vertical. In-scope
topics, primary trust-tier domains, and embargo rules are defined there. Items
labeled outside the in-scope topic list will still load but should be flagged.

## Schema

Required fields (the harness runner reads these):

| Field | Type | Notes |
|---|---|---|
| `id` | str | Stable identifier — must not change once published |
| `source_url` | str | Real, verifiable URL. Use `https://example.invalid/...` for placeholders |
| `source_text` | str | Plain text of the source article (or relevant section) |
| `statement` | str | The claim, paraphrased — distinct from the verbatim span |
| `expected_status` | enum | `likely_true` \| `contested` \| `unverified` |
| `expected_verbatim_span` | str | The literal span in `source_text` that supports the claim |
| `expected_char_start` | int \| null | Inclusive offset in `source_text`. Null until enriched |
| `expected_char_end` | int \| null | Exclusive offset. Null until enriched |
| `notes` | str | Free text |

Optional metadata:

| Field | Type | Notes |
|---|---|---|
| `vertical` | str | Defaults to `"geopolitics"` |
| `claim_type` | enum | `factual` \| `quantitative` \| `attribution` \| `temporal` |
| `entities` | list[GoldEntity] | `{name, qid?, role?}`. Use Wikidata QIDs |
| `trust_tier` | int | 1 (best) … 4 (unvetted). See `config/trust_tiers.yaml` |
| `publisher` | str | e.g. `"Reuters"` |
| `published_at` | str | ISO-8601 date |
| `labeler` | str | Who labeled it |
| `labeler_notes` | str | Per-item caveats — especially URL/offset placeholders |
| `verified` | bool | `false` until URL+span+offsets are confirmed against the live article |
| `created_at` | datetime | When the row was first labeled |

## Verbatim span policy

**The span must literally exist in `source_text`.** This is the core invariant —
the programmatic verifier (`packages/extraction/src/argus_extraction/verifier.py`)
rejects any extracted claim whose verbatim span is not character-for-character
present in the source.

Char offsets are **filled at enrichment time**, not at labeling time. The
labeler writes the span and a placeholder URL; an enrichment script (TODO,
not yet built) fetches the article, locates the span, and fills offsets.
Until then, `expected_char_start` / `expected_char_end` stay `null` and the
runner's span-precision metric reports 0 for that item — which is correct
behavior (we never count an unenriched item as a citation hit).

## Adding new items

1. Pick a topic in `topics_in_scope`.
2. Find a tier-1 source (Reuters / AP / AFP / official press release).
3. Copy the relevant paragraph into `source_text`.
4. Pick the verbatim span and write the paraphrased claim.
5. Set `verified: false` and offsets to `null`.
6. Mark the placeholder URL in `labeler_notes` if not yet a permanent link.
7. Run `uv run pytest eval/tests/`.

## Running the harness

```bash
uv run python -m eval.harness.runner --gold ./eval/gold.jsonl --output ./eval/results.json
```

The runner runs `argus_extraction.ClaimExtractor` against each `source_text`
and emits citation precision/recall, exact-match rate, hallucination rate.

## What's intentionally not here

- A labeling UI (overkill for hackathon scale; jsonl + editor is enough).
- An enrichment script that fetches articles and fills offsets — needed
  before the eval has real teeth. This is a 100-line script that hits the
  source URLs, locates the span via fuzzy match, and emits the offsets.
- Inter-annotator agreement scoring — single-labeler is fine for now.
