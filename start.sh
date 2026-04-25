#!/usr/bin/env bash
# Start Argus dev stack: API + frontend (and optionally Temporal worker).
# Usage: ./start.sh [--with-worker]
# Ctrl-C stops everything; if any process dies, the rest are killed.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

with_worker=0
for arg in "$@"; do
    case "$arg" in
        --with-worker) with_worker=1 ;;
        -h|--help)
            cat <<USAGE
Usage: $0 [--with-worker]

Starts:
  - FastAPI (uvicorn --reload) on http://localhost:8000
  - Next.js (pnpm dev)         on http://localhost:3000
  - Temporal worker if --with-worker (only useful when temporal server is up)

Ctrl-C or any one process exiting brings everything down.
USAGE
            exit 0
            ;;
        *)
            echo "Unknown arg: $arg" >&2
            exit 2
            ;;
    esac
done

if [ ! -f .env ]; then
    echo "ERROR: .env missing. Copy .env.example to .env and fill it in." >&2
    exit 1
fi

# Source nvm + use Node 22 for the frontend subshell. Backend doesn't care.
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    # shellcheck disable=SC1090
    . "$NVM_DIR/nvm.sh"
    nvm use 22 >/dev/null 2>&1 || echo "[start.sh] warn: nvm use 22 failed; using $(node -v 2>/dev/null || echo 'no node')"
fi

pids=()

cleanup() {
    echo
    echo "[start.sh] shutting down..."
    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            # Kill the whole process group (uvicorn reloader spawns a child, etc.)
            pkill -TERM -P "$pid" 2>/dev/null || true
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    sleep 0.5
    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL "$pid" 2>/dev/null || true
        fi
    done
    echo "[start.sh] done"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "[start.sh] starting API on http://localhost:8000"
uv run uvicorn argus_api.main:app --reload --host 0.0.0.0 --port 8000 &
pids+=($!)

if [ "$with_worker" -eq 1 ]; then
    echo "[start.sh] starting Temporal worker"
    uv run python -m argus_workers.main &
    pids+=($!)
fi

echo "[start.sh] starting frontend on http://localhost:3000"
(cd apps/web && pnpm dev) &
pids+=($!)

echo
echo "[start.sh] all up. Ctrl-C to stop."
echo "    API       http://localhost:8000   (docs: http://localhost:8000/docs)"
echo "    Frontend  http://localhost:3000"
if [ "$with_worker" -eq 1 ]; then
    echo "    Worker    Temporal task queue: argus-default"
fi
echo

# wait -n returns when ANY child exits; cleanup trap then kills the rest.
wait -n
