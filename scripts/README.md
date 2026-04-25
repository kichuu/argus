# scripts/

Local development runners. Everything assumes you have:

- Postgres on `localhost:5432` with database `argus`, user `argus/argus`
- `OPENAI_API_KEY` set in `.env`
- (Optional) Apache AGE extension installed in the cluster
- (Optional) Qdrant on `localhost:6333` — needed for vector retrieval, not for baseline
- (Optional) Temporal dev server — needed only if you run the worker (`apps/workers`)

## First-time setup

```bash
# 1. Activate the workspace (creates .venv with all package deps)
uv sync

# 2. Apply DB migrations (creates tables; tries to enable AGE — non-fatal if missing)
uv run alembic upgrade head

# 3. Verify everything before running the pipeline
uv run python scripts/preflight.py
```

The preflight checks: OpenAI key, Postgres reachability, alembic head, AGE
extension, and whether your configured model IDs actually exist in your OpenAI
account. The model-ID check is the one that catches bugs from hallucinated
names like `gpt-5.5` left over in `.env.example`.

## Run the Phase 4 baseline against a real feed

```bash
uv run python scripts/run_baseline.py --rss https://feeds.bbci.co.uk/news/world/rss.xml --max-items 1
```

This calls the Temporal activity functions directly (skipping the Temporal
server). It runs `fetch_source -> extract_claims -> verify_claims` end-to-end
and prints what landed in the DB at each stage.

Tip: `--max-items 1` while debugging — extraction is the biggest LLM cost.

## Other scripts

- `init_db.py` — older bootstrap (still works); `alembic upgrade head` is preferred
- `init_qdrant.py` — creates the `argus_evidence` collection in Qdrant
- `seed_sources.py` — seeds a small set of source rows for development

## Things that won't work yet

- **No `/discussions` POST trigger from the frontend.** The Phase 4 pipeline
  has to be kicked off from this script (or a Temporal client) until the
  FastAPI route is wired.
- **`index_evidence` is a no-op.** Sources persist to Postgres but don't get
  embedded into Qdrant yet.
- **AGE graph stays empty.** No worker syncs `entities` rows into the graph.
- **Gold-set offsets are null.** `eval/gold.jsonl` items need an enrichment
  pass to fill `expected_char_start` / `expected_char_end` before the citation
  precision metric is meaningful.
