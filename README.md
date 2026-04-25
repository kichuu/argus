# Argus

Argus is a citation-grounded research and news platform: it ingests primary sources,
extracts claims with verbatim spans, cross-checks them with an adversarial verifier,
and then runs a multi-agent debate over the verified evidence to produce a final
claim ledger. OpenAI is the only LLM provider; the pipeline is committed to a
single vertical (geopolitics) for v1.

## Status

What works today (Phase 4):

- RSS + GDELT ingestion, content-hash + simhash dedup, raw-text store on local fs.
- Claim extraction with verbatim-span verification (drops claims whose spans don't
  match the source text).
- Cross-class adversarial verifier (chat-class extractor vs. reasoning-class
  verifier; configured via `DEFAULT_EXTRACTOR_MODEL` / `DEFAULT_VERIFIER_MODEL`).
- Multi-agent discussion graph (research / persona / critic / synthesizer).
- Postgres persistence for sources, claims, discussions, and agent messages.
- End-to-end demo runner (`scripts/run_full_demo.py`) that calls the activity
  functions directly, no Temporal required.

Still scaffolded:

- `index_evidence` is a no-op; Qdrant collection exists but no embedding worker.
- AGE graph stays empty: there's no entity-sync activity yet, so graph queries
  return `[]`.
- `/discussions` POST trigger from the frontend isn't wired — kick off runs
  with `scripts/run_full_demo.py` (or a Temporal client).
- `eval/gold.jsonl` placeholder URLs are marked `verified: false`; expected
  span offsets are `null` until enrichment.

## Architecture

- **`apps/api`** — FastAPI service; read endpoints over the claim ledger and
  discussion runs.
- **`apps/web`** — Next.js 15 frontend (debate room, persona reference graph,
  Zustand stores).
- **`apps/workers`** — Temporal worker; consumes the `argus-default` task queue
  and runs ingestion + discussion workflows.
- **`packages/core`** — settings, SQLAlchemy models, pydantic schemas, logging.
- **`packages/ingestion`** — RSS, GDELT, raw-store, dedup.
- **`packages/extraction`** — claim extractor, span verifier, adversarial
  verifier, OpenAI provider.
- **`packages/retrieval`** — Qdrant vector retriever and AGE graph querier
  (hybrid retrieval, currently bypassed for the baseline evidence pack).
- **`packages/agents`** — research, persona, critic, master, synthesizer agents
  composed into a `DiscussionGraph`.

Infra: Postgres (sources, claims, discussions, agent messages) + Apache AGE
(entity graph) + Qdrant (`argus_evidence` collection) + S3-compatible object
store (RustFS / MinIO; falls back to local fs) + OpenAI.

## Quickstart

10-minute demo path. Assumes Postgres is running locally.

1. **Prereqs.** Python 3.12, [`uv`](https://docs.astral.sh/uv/), Node 20+,
   `pnpm`, Postgres 14+ with the [Apache AGE](https://age.apache.org/) extension
   installed in your cluster. Optionally: Qdrant on `:6333` and a Temporal dev
   server.

2. **Configure env.**

   ```bash
   cp .env.example .env
   ```

   Fill `OPENAI_API_KEY`. **Verify the model IDs against
   `platform.openai.com/docs/models` before running** — earlier drafts shipped
   with `gpt-5.4` / `gpt-5.5`, which are not real model IDs. Use a current chat
   model (e.g. `gpt-4.1`) for the extractor / persona / synth slots and a
   reasoning model (e.g. `o4-mini`) for the verifier. The extractor and
   verifier must be a different model class.

3. **Install.**

   ```bash
   uv sync
   ```

4. **Migrate.**

   ```bash
   uv run alembic upgrade head
   ```

   Migration `0002` is a no-op on the SQL side; `argus_retrieval.graph` lazily
   runs `CREATE EXTENSION age` / `LOAD 'age'` / `create_graph` at first use.
   That requires a role with extension-create privilege (typically superuser).

5. **(Optional) initialize Qdrant.**

   ```bash
   uv run python scripts/init_qdrant.py
   ```

6. **Preflight.** Confirm everything is green before spending tokens:

   ```bash
   uv run python scripts/preflight.py
   ```

   This checks the OpenAI key, Postgres reachability, alembic head, the AGE
   extension, and that each configured model ID actually exists in your
   account. Fix any red lines first.

7. **Run the full demo.**

   ```bash
   uv run python scripts/run_full_demo.py \
       --rss https://feeds.bbci.co.uk/news/world/rss.xml \
       --max-items 1 \
       --topic "What does this week's news mean for NATO posture toward Russia?"
   ```

   This walks fetch -> extract -> verify -> index -> start_discussion ->
   assemble_evidence_pack -> run_discussion_graph -> persist_results -> ledger.
   Add `--skip-discuss` to run only the ingestion path (equivalent to
   `scripts/run_baseline.py`).

8. **Backend API.**

   ```bash
   uv run uvicorn argus_api.main:app --reload
   ```

9. **Worker (optional, only if you want Temporal-driven runs).**

   ```bash
   temporal server start-dev
   uv run python -m argus_workers.main
   ```

10. **Frontend.**

    ```bash
    cd apps/web && pnpm install && pnpm dev
    ```

## Eval harness

```bash
uv run pytest eval/tests/ -q
```

The gold set lives at `eval/gold.jsonl`. Items currently use placeholder URLs
(marked `verified: false`) and have `expected_char_start` / `expected_char_end`
set to `null`; the citation-precision metric only becomes meaningful once those
offsets are filled. See `eval/README.md`.

## Vertical

Argus is committed to a single vertical: **geopolitics**.

- `config/vertical.yaml` — in-scope topics and primary domains.
- `config/trust_tiers.yaml` — publisher trust assignments used during ingestion.

## Known limitations

- `index_evidence` is a no-op; sources land in Postgres but aren't embedded into
  Qdrant. The full-demo script handles this gracefully — Qdrant being down does
  not fail the run.
- AGE graph queries return `[]` until an entity-sync worker is added.
- AGE setup needs a role with extension-create privilege (typically superuser);
  if the cluster role can't `CREATE EXTENSION age`, grant it with a one-shot
  superuser session (`ALTER ROLE argus SUPERUSER`) or pre-install the extension.
- Model IDs in `.env.example` historically include hallucinated values
  (`gpt-5.4`, `gpt-5.5`). Always run `scripts/preflight.py` after editing
  `.env`.
- No `/discussions` POST endpoint yet; kick off runs from
  `scripts/run_full_demo.py` or a Temporal client.
- Gold-set offsets are null; citation-precision metric is not yet meaningful.

## License / credits

License: TBD. Copyright the Argus contributors.
