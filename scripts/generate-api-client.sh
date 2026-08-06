#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
if [[ -n "$mode" && "$mode" != "--check" ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
schema_path="$repo_root/frontend/openapi/company-system.openapi.json"
client_path="$repo_root/frontend/src/api/generated/company-system.ts"
orval_bin="$repo_root/frontend/node_modules/.bin/orval"

if [[ ! -x "$repo_root/backend/.venv/bin/python" ]]; then
  echo "Missing backend/.venv; install backend development dependencies first." >&2
  exit 1
fi

if [[ ! -x "$orval_bin" ]]; then
  echo "Missing frontend dependencies; run 'make bootstrap' first." >&2
  exit 1
fi

export_schema() {
  local output_path="$1"
  (
    cd "$repo_root/backend"
    APP_ENV=test \
    APP_HOST=127.0.0.1 \
    APP_PORT=8000 \
    DATABASE_URL='postgresql+psycopg://company_system_test:openapi-only@127.0.0.1/company_system_test' \
      .venv/bin/python scripts/export_openapi.py --output "$output_path"
  )
}

generate_client() {
  local input_path="$1"
  local output_path="$2"
  (
    cd "$repo_root/frontend"
    ORVAL_INPUT="$input_path" ORVAL_OUTPUT="$output_path" \
      "$orval_bin" --config orval.config.ts --fail-on-warnings
  )
}

if [[ "$mode" == "--check" ]]; then
  temporary_dir="$(mktemp -d)"
  trap 'rm -rf -- "$temporary_dir"' EXIT
  temporary_schema="$temporary_dir/company-system.openapi.json"
  temporary_client="$temporary_dir/company-system.ts"
  export_schema "$temporary_schema"
  generate_client "$temporary_schema" "$temporary_client"

  cmp --silent "$schema_path" "$temporary_schema" || {
    echo "OpenAPI snapshot is stale. Run: npm run api:generate" >&2
    exit 1
  }
  cmp --silent "$client_path" "$temporary_client" || {
    echo "Generated TypeScript client is stale. Run: npm run api:generate" >&2
    exit 1
  }
  echo "OpenAPI snapshot and TypeScript client are current."
  exit 0
fi

mkdir -p "$(dirname "$schema_path")" "$(dirname "$client_path")"
export_schema "$schema_path"
generate_client "$schema_path" "$client_path"
echo "Generated OpenAPI snapshot and TypeScript client."
