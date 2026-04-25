# argus-workers

Temporal worker for the Argus Phase 4 pipeline. Consumes jobs from the
`argus-default` task queue (configurable via `TEMPORAL_TASK_QUEUE`) and runs
ingestion and discussion workflows.

## What this worker does

- **Ingestion path** (`IngestionWorkflow`): for each source config it calls
  `fetch_source`, then for every persisted source `extract_claims`,
  `verify_claims`, and `index_evidence`. Fetch is retried on transient HTTP
  failures; LLM-driven activities run with `maximum_attempts=1` so a partially
  charged extraction never reruns silently.
- **Discussion path** (`DiscussionWorkflow`): `start_discussion` ->
  `assemble_evidence_pack` -> `run_discussion_graph` -> `persist_results`. The
  graph step has the longest timeout (300 s) because it spans research +
  personas + critic + synthesizer.

## Run it

The worker needs a Temporal server. The dev server is the easiest option:

```bash
# in one terminal
temporal server start-dev

# in another, from the repo root
uv run python -m argus_workers.main
```

It connects using `TEMPORAL_HOST`, `TEMPORAL_NAMESPACE`, and
`TEMPORAL_TASK_QUEUE` from your `.env` (defaults: `localhost:7233`, `default`,
`argus-default`). The worker also needs the same Postgres / OpenAI / Qdrant
configuration the rest of the stack uses — see the root `README.md` and
`scripts/preflight.py`.

## Registered workflows and activities

Workflows:

- `IngestionWorkflow` — fetch -> extract -> verify -> index per source.
- `DiscussionWorkflow` — start -> assemble -> graph -> persist.

Activities:

- `fetch_source(config)` -> list of source IDs.
- `extract_claims(source_id)` -> list of claim IDs.
- `verify_claims(claim_ids)` -> dict with `verified` count and per-claim
  verdicts.
- `index_evidence(source_id)` -> currently a recorded no-op (Qdrant indexing
  TBD).
- `start_discussion(topic, vertical, discussion_id?)` -> discussion ID.
- `assemble_evidence_pack(discussion_id)` -> dict with `evidence_count`.
- `run_discussion_graph(discussion_id)` -> graph state with `messages` and
  `final_claims`.
- `persist_results(discussion_id, graph_result)` -> persistence summary.

## Testing without a worker

You don't need Temporal running to exercise the pipeline. The activities are
plain async functions decorated with `@activity.defn`; the demo runner calls
them directly:

```bash
uv run python scripts/run_full_demo.py \
    --rss https://feeds.bbci.co.uk/news/world/rss.xml \
    --topic "Your discussion topic"
```

That script walks the same stages as `IngestionWorkflow` followed by
`DiscussionWorkflow`, with one source config and one topic. Use it for local
demos and debugging; use the worker when you want retries, scheduling, and
durable workflow history.
