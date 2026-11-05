#!/usr/bin/env bash
# Run a command against a throwaway, synthetic-only Ghost Texter backend.
#
# Usage: run-demo.sh [command ...]
# With no command, runs the API walkthrough. The command receives GHOST_DEMO_URL
# and GHOST_DEMO_TOKEN. The server and its data are removed on exit.
#
# Port 8001 is deliberate: authorize() in backend/ghost/main.py trusts browser
# origins on 8001 and 5173 only, so UI actions from any other port get a 403.
set -euo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPTS/../../../.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
PORT=8001
URL="http://127.0.0.1:$PORT"

if [ ! -x "$PYTHON" ]; then
  echo "REFUSED: $PYTHON not found. Run: uv sync --extra dev" >&2
  exit 3
fi

# Any listener here could be the user's live backend. Never test against it,
# and never stop it on the user's behalf.
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "REFUSED: port $PORT is in use and may be the live backend. Ask the user to stop it." >&2
  exit 3
fi

WORKDIR="$(mktemp -d)"
TOKEN="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(32))')"
SERVER_PID=""

cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

# Settings reads .env relative to the working directory. Starting from the empty
# temp directory means the user's .env is never loaded, and the explicit values
# below override anything inherited from this shell.
(
  cd "$WORKDIR"
  exec env \
    GHOST_MODE=demo \
    GHOST_LLM=false \
    GHOST_SEND_ENABLED=false \
    GHOST_ALLOWED_RECIPIENTS='[]' \
    GHOST_DATA_DIR="$WORKDIR/data" \
    GHOST_API_TOKEN="$TOKEN" \
    OPENAI_API_KEY= \
    "$PYTHON" -m uvicorn ghost.main:create_app --factory \
      --host 127.0.0.1 --port "$PORT" --log-level warning
) >"$WORKDIR/server.log" 2>&1 &
SERVER_PID=$!

export GHOST_DEMO_URL="$URL"
export GHOST_DEMO_TOKEN="$TOKEN"

# The random token means only the server started above can answer successfully.
ready=""
for _ in $(seq 1 60); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "REFUSED: demo server exited during startup. Its log is withheld; rerun to debug." >&2
    exit 3
  fi
  if "$PYTHON" "$SCRIPTS/api_walkthrough.py" --check-only >/dev/null 2>&1; then
    ready=1
    break
  fi
  /bin/sleep 0.5
done
if [ -z "$ready" ]; then
  echo "REFUSED: could not confirm a synthetic demo server on port $PORT." >&2
  exit 3
fi
echo "Demo server confirmed: mode=demo, llm off, sending off, synthetic recipients only."

if [ "$#" -eq 0 ]; then
  set -- "$PYTHON" "$SCRIPTS/api_walkthrough.py"
fi
"$@"
