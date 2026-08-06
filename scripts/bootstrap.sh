#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
python_bin="${PYTHON_BIN:-python3.12}"

if [[ ! -f "$repo_root/.env" ]]; then
  install -m 600 "$repo_root/.env.example" "$repo_root/.env"
  echo "Created .env from .env.example. Replace POSTGRES_PASSWORD before make dev."
fi

if [[ ! -x "$repo_root/backend/.venv/bin/python" ]]; then
  "$python_bin" -m venv "$repo_root/backend/.venv"
fi

"$repo_root/backend/.venv/bin/python" -m pip install -e "$repo_root/backend[dev]"
(
  cd "$repo_root/frontend"
  ../scripts/npm11.sh ci
)

echo "Dependencies installed. Run 'make env-check' after replacing the local password."
