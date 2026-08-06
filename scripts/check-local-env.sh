#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
env_file="${1:-$repo_root/.env}"

if [[ ! -f "$env_file" ]]; then
  echo "Missing .env. Run 'make bootstrap', then replace the local password." >&2
  exit 1
fi

password_line="$(grep -E '^POSTGRES_PASSWORD=' "$env_file" | tail -n 1 || true)"
password="${password_line#POSTGRES_PASSWORD=}"
password="$(printf '%s' "$password" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"

if [[ "$password" == \"*\" && "$password" == *\" ]]; then
  password="${password:1:${#password}-2}"
elif [[ "$password" == \'*\' && "$password" == *\' ]]; then
  password="${password:1:${#password}-2}"
else
  password="$(printf '%s' "$password" | sed -E 's/[[:space:]]+#.*$//; s/[[:space:]]+$//')"
fi

password_without_whitespace="$(printf '%s' "$password" | tr -d '[:space:]')"

if [[ -z "$password_line" || -z "$password_without_whitespace" || "$password" == "replace-with-local-only-password" ]]; then
  echo "POSTGRES_PASSWORD must be replaced with a non-placeholder local password." >&2
  exit 1
fi

if [[ "$env_file" == "$repo_root/.env" ]]; then
  python_bin="$repo_root/backend/.venv/bin/python"
  if [[ ! -x "$python_bin" ]]; then
    echo "Missing backend/.venv. Run 'make bootstrap' first." >&2
    exit 1
  fi
  (
    cd "$repo_root/backend"
    "$python_bin" -c 'from app.core.config import load_settings; load_settings()'
  )
fi

echo "Local environment file passed the non-secret readiness check."
