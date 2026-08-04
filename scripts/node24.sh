#!/usr/bin/env bash
set -euo pipefail

current_node="$(node --version 2>/dev/null || true)"

if [[ "$current_node" =~ ^v24\. ]]; then
  exec node "$@"
fi

npm_cache="$(npm config get cache 2>/dev/null || true)"
if [[ -d "$npm_cache/_npx" ]]; then
  for cached_bin in "$npm_cache"/_npx/*/node_modules/.bin; do
    [[ -x "$cached_bin/node" ]] || continue
    cached_version="$($cached_bin/node --version 2>/dev/null || true)"
    if [[ "$cached_version" =~ ^v24\. ]]; then
      exec "$cached_bin/node" "$@"
    fi
  done
fi

exec npx --yes --package node@24 node "$@"
