#!/usr/bin/env bash
# PHANTOM dev starter (macOS/Linux)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

(cd "$ROOT/backend" && ./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8899 --reload) &
BACK_PID=$!
(cd "$ROOT/frontend" && npm run dev) &
FRONT_PID=$!

trap "kill $BACK_PID $FRONT_PID 2>/dev/null" EXIT
echo "PHANTOM dev: backend :8899, frontend :5173"
wait
