#!/usr/bin/env bash
set -euo pipefail

required_node_major=24
required_npm_major=11

current_node="$(node --version 2>/dev/null || true)"
current_npm="$(npm --version 2>/dev/null || true)"

if [[ "$current_node" =~ ^v${required_node_major}\. ]] && [[ "$current_npm" =~ ^${required_npm_major}\. ]]; then
  exec npm "$@"
fi

npm_cache="$(npm config get cache 2>/dev/null || true)"
if [[ -d "$npm_cache/_npx" ]]; then
  for cached_bin in "$npm_cache"/_npx/*/node_modules/.bin; do
    [[ -x "$cached_bin/node" && -x "$cached_bin/npm" ]] || continue
    cached_node="$($cached_bin/node --version 2>/dev/null || true)"
    cached_npm="$($cached_bin/npm --version 2>/dev/null || true)"
    if [[ "$cached_node" =~ ^v${required_node_major}\. ]] && [[ "$cached_npm" =~ ^${required_npm_major}\. ]]; then
      exec env PATH="$cached_bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin" "$cached_bin/npm" "$@"
    fi
  done
fi

echo "Using an isolated Node 24 / npm 11 toolchain for this command." >&2
exec npx --yes --package node@24 --package npm@11.19.0 npm "$@"
