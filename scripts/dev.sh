#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM
  [[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
  [[ -n "$backend_pid" ]] && kill "$backend_pid" 2>/dev/null || true
  [[ -n "$frontend_pid" ]] && wait "$frontend_pid" 2>/dev/null || true
  [[ -n "$backend_pid" ]] && wait "$backend_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

"$repo_root/scripts/check-local-env.sh"
cd "$repo_root"
docker compose up -d --wait postgres

(
  cd backend
  .venv/bin/alembic upgrade head
  exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
backend_pid="$!"

(
  cd frontend
  exec ../scripts/npm11.sh run dev -- --host 127.0.0.1
) &
frontend_pid="$!"

echo "Frontend: http://127.0.0.1:5173"
echo "API docs: http://127.0.0.1:8000/docs"
echo "Press Ctrl-C to stop frontend and backend; PostgreSQL remains until 'make down'."
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

echo "A development process stopped unexpectedly; shutting down the other process." >&2
exit 1
