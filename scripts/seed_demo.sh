#!/usr/bin/env bash
# Argus demo bootstrap: take a fresh DB to a fully-populated demo state.
#
# Stages: preflight -> migrate -> seed personas -> ingest a small feed roster
# -> launch one demo discussion -> poll until it completes -> summary.
#
# Usage:
#     chmod +x scripts/seed_demo.sh   # one-time, if not already set
#     ./scripts/seed_demo.sh
#
# Requires the API to be running in another terminal:
#     uv run uvicorn argus_api.main:app --port 8000
#
# This script does NOT start the API itself, because it must orchestrate
# both the DB bootstrap and an HTTP-driven discussion launch, and we want
# to keep API lifecycle (logs, restarts) under the operator's control.

set -euo pipefail

# ---------------------------------------------------------------------------
# resolve repo root so the script works regardless of CWD
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# ---------------------------------------------------------------------------
# colors (TTY-only; degrade gracefully)
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
    C_RESET=$'\033[0m'
    C_BOLD=$'\033[1m'
    C_RED=$'\033[31m'
    C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'
    C_BLUE=$'\033[34m'
    C_CYAN=$'\033[36m'
else
    C_RESET=''
    C_BOLD=''
    C_RED=''
    C_GREEN=''
    C_YELLOW=''
    C_BLUE=''
    C_CYAN=''
fi

stage() {
    # $1 = "[N/7]"  $2 = label
    printf '\n%s%s%s %s%s%s\n' "${C_BOLD}" "$1" "${C_RESET}" "${C_CYAN}" "$2" "${C_RESET}"
}

ok()    { printf '  %sOK%s    %s\n' "${C_GREEN}"  "${C_RESET}" "$1"; }
warn()  { printf '  %sWARN%s  %s\n' "${C_YELLOW}" "${C_RESET}" "$1"; }
err()   { printf '  %sERR%s   %s\n' "${C_RED}"    "${C_RESET}" "$1"; }
info()  { printf '  %s..%s    %s\n' "${C_BLUE}"   "${C_RESET}" "$1"; }

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
API_BASE="${ARGUS_API_BASE:-http://localhost:8000}"
DEFAULT_DEMO_TOPIC="What does this week of reporting imply for NATO posture toward Russia, and which claims remain unverified?"
DEMO_TOPIC="${ARGUS_DEMO_TOPIC:-${DEFAULT_DEMO_TOPIC}}"
DEMO_VERTICAL="${ARGUS_DEMO_VERTICAL:-geopolitics}"
POLL_INTERVAL_SEC=8
POLL_TIMEOUT_SEC=240   # 4 minutes
FALLBACK_RSS="https://feeds.bbci.co.uk/news/world/rss.xml"

# ---------------------------------------------------------------------------
# [1/7] preflight
# ---------------------------------------------------------------------------
stage "[1/7]" "preflight (env, DB, models)"
if ! uv run python scripts/preflight.py; then
    err "preflight failed; fix the above and re-run."
    exit 1
fi
ok "preflight passed"

# ---------------------------------------------------------------------------
# [2/7] migrations
# ---------------------------------------------------------------------------
stage "[2/7]" "alembic upgrade head"
uv run alembic upgrade head
ok "schema at head"

# ---------------------------------------------------------------------------
# [3/7] seed personas
# ---------------------------------------------------------------------------
stage "[3/7]" "seed stock personas"
uv run python scripts/seed_personas.py
ok "personas ready"

# ---------------------------------------------------------------------------
# [4/7] ingest a small feed roster (best-effort)
# ---------------------------------------------------------------------------
stage "[4/7]" "ingest a small feed roster"
USED_FALLBACK_INGEST=0
if [ -f scripts/ingest_roster.py ]; then
    info "found scripts/ingest_roster.py — running batch ingest with --max-items-override 2"
    if uv run python scripts/ingest_roster.py --max-items-override 2; then
        ok "feed roster ingested"
    else
        warn "ingest_roster.py exited non-zero; continuing (some feeds may have failed)"
    fi
else
    warn "scripts/ingest_roster.py not present — falling back to a single BBC feed"
    USED_FALLBACK_INGEST=1
    # Use --skip-discuss so the fallback only ingests + extracts + verifies;
    # we still run our own discussion in [5/7] via the API.
    if uv run python scripts/run_full_demo.py \
            --rss "${FALLBACK_RSS}" \
            --topic "Demo seed" \
            --max-items 2 \
            --skip-discuss; then
        ok "fallback ingest finished"
    else
        warn "fallback ingest failed; continuing — discussion may have empty evidence"
    fi
fi

# ---------------------------------------------------------------------------
# [5/7] launch the demo discussion via the API
# ---------------------------------------------------------------------------
stage "[5/7]" "launch demo discussion"

# Verify the API is up. Use --max-time so we don't hang forever.
if ! curl -fsS --max-time 3 "${API_BASE}/health" >/dev/null 2>&1; then
    err "API not running at ${API_BASE}."
    err "Start it with: ${C_BOLD}uv run uvicorn argus_api.main:app --port 8000${C_RESET}"
    err "in another terminal, then re-run this script."
    exit 1
fi
ok "API reachable at ${API_BASE}"

info "POST ${API_BASE}/discussions  topic=\"${DEMO_TOPIC}\""

# Build JSON body via python to handle quoting safely.
export DEMO_TOPIC DEMO_VERTICAL
BODY_JSON="$(python3 -c 'import json,os;print(json.dumps({"topic":os.environ["DEMO_TOPIC"],"vertical":os.environ["DEMO_VERTICAL"]}))')"

START_RESPONSE="$(
    curl -fsS -X POST "${API_BASE}/discussions" \
        -H "Content-Type: application/json" \
        -d "${BODY_JSON}"
)" || {
    err "POST /discussions failed."
    exit 1
}

DISCUSSION_ID="$(
    printf '%s' "${START_RESPONSE}" \
        | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])'
)"
if [ -z "${DISCUSSION_ID}" ]; then
    err "could not parse discussion id from response: ${START_RESPONSE}"
    exit 1
fi
ok "discussion launched id=${DISCUSSION_ID}"

# ---------------------------------------------------------------------------
# [6/7] poll for completion (max 4 minutes)
# ---------------------------------------------------------------------------
_minutes=$((POLL_TIMEOUT_SEC / 60))
stage "[6/7]" "wait for completion - max ${_minutes} min"
ELAPSED=0
FINAL_STATUS=""
while [ "${ELAPSED}" -lt "${POLL_TIMEOUT_SEC}" ]; do
    DETAIL_JSON="$(
        curl -fsS --max-time 5 "${API_BASE}/discussions/${DISCUSSION_ID}" || true
    )"
    if [ -z "${DETAIL_JSON}" ]; then
        warn "no response from /discussions/${DISCUSSION_ID}; retrying"
    else
        FINAL_STATUS="$(
            printf '%s' "${DETAIL_JSON}" \
                | python3 -c 'import json,sys;print(json.load(sys.stdin).get("status",""))' \
                2>/dev/null || true
        )"
        info "t=${ELAPSED}s status=${FINAL_STATUS:-?}"
        case "${FINAL_STATUS}" in
            completed|failed)
                break
                ;;
        esac
    fi
    sleep "${POLL_INTERVAL_SEC}"
    ELAPSED=$((ELAPSED + POLL_INTERVAL_SEC))
done

if [ -z "${FINAL_STATUS}" ]; then
    warn "never observed a status; the API may be unresponsive"
elif [ "${FINAL_STATUS}" = "completed" ]; then
    ok "discussion completed in ~${ELAPSED}s"
elif [ "${FINAL_STATUS}" = "failed" ]; then
    err "discussion failed (see API logs / GET ${API_BASE}/discussions/${DISCUSSION_ID})"
else
    warn "timed out at ${POLL_TIMEOUT_SEC}s with status=${FINAL_STATUS}"
fi

# ---------------------------------------------------------------------------
# [7/7] summary
# ---------------------------------------------------------------------------
stage "[7/7]" "summary"

CLAIMS_JSON="$(
    curl -fsS --max-time 5 "${API_BASE}/discussions/${DISCUSSION_ID}/claims" || true
)"

if [ -z "${CLAIMS_JSON}" ]; then
    warn "could not fetch claims"
    CLAIM_COUNT=0
else
    if command -v jq >/dev/null 2>&1; then
        CLAIM_COUNT="$(printf '%s' "${CLAIMS_JSON}" | jq 'length')"
    else
        CLAIM_COUNT="$(
            printf '%s' "${CLAIMS_JSON}" \
                | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))'
        )"
    fi
fi

printf '\n  %sdiscussion_id%s  %s\n' "${C_BOLD}" "${C_RESET}" "${DISCUSSION_ID}"
printf '  %sstatus%s         %s\n'  "${C_BOLD}" "${C_RESET}" "${FINAL_STATUS:-unknown}"
printf '  %sclaims%s         %s\n'  "${C_BOLD}" "${C_RESET}" "${CLAIM_COUNT}"
if [ "${USED_FALLBACK_INGEST}" = "1" ]; then
    printf '  %singest%s         fallback (single BBC feed)\n' "${C_BOLD}" "${C_RESET}"
else
    printf '  %singest%s         roster\n' "${C_BOLD}" "${C_RESET}"
fi

if [ "${CLAIM_COUNT:-0}" != "0" ] && [ -n "${CLAIMS_JSON}" ]; then
    printf '\n  %stop claims%s\n' "${C_BOLD}" "${C_RESET}"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "${CLAIMS_JSON}" \
            | jq -r '.[0:3][] | "    - [\(.status)] conf=\(.confidence)  \(.statement)"'
    else
        printf '%s' "${CLAIMS_JSON}" | python3 - <<'PY'
import json, sys
data = json.load(sys.stdin)
for c in data[:3]:
    statement = (c.get("statement") or "").strip().replace("\n", " ")
    if len(statement) > 200:
        statement = statement[:200] + "..."
    conf = c.get("confidence", 0.0)
    try:
        conf_str = f"{float(conf):.2f}"
    except (TypeError, ValueError):
        conf_str = str(conf)
    print(f"    - [{c.get('status', '?')}] conf={conf_str}  {statement}")
PY
    fi
fi

printf '\n  %snext%s            open the frontend or hit %s/discussions/%s\n' \
    "${C_BOLD}" "${C_RESET}" "${API_BASE}" "${DISCUSSION_ID}"
printf '\n%sdone.%s\n' "${C_GREEN}${C_BOLD}" "${C_RESET}"
