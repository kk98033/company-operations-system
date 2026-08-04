#!/usr/bin/env bash
set -euo pipefail

required_node_major=24
minimum_python_major=3
minimum_python_minor=12
maximum_python_minor=15

node_bin="${NODE_BIN:-node}"
npm_bin="${NPM_BIN:-npm}"
python_bin="${PYTHON_BIN:-python3}"

node_version="$($node_bin --version 2>/dev/null || true)"
npm_version="$($npm_bin --version 2>/dev/null || true)"
python_version="$($python_bin --version 2>/dev/null || true)"

if [[ ! "$node_version" =~ ^v([0-9]+)\. ]]; then
  echo "Node.js is missing. Install Node.js 24 LTS." >&2
  exit 1
fi

node_major="${BASH_REMATCH[1]}"
if (( node_major != required_node_major )); then
  echo "Node.js $node_version does not match this project. Use Node.js 24 LTS." >&2
  exit 1
fi

if [[ ! "$npm_version" =~ ^([0-9]+)\. ]]; then
  echo "npm is missing. Use npm 11." >&2
  exit 1
fi

npm_major="${BASH_REMATCH[1]}"
if (( npm_major != 11 )); then
  echo "npm $npm_version does not match this project. Use npm 11." >&2
  exit 1
fi

if [[ ! "$python_version" =~ ^Python\ ([0-9]+)\.([0-9]+)\. ]]; then
  echo "Python is missing. Install Python 3.12 or newer supported version." >&2
  exit 1
fi

python_major="${BASH_REMATCH[1]}"
python_minor="${BASH_REMATCH[2]}"
if (( python_major != minimum_python_major || python_minor < minimum_python_minor || python_minor >= maximum_python_minor )); then
  echo "$python_version does not match this project. Use Python >=3.12,<3.15." >&2
  exit 1
fi

docker --version >/dev/null
docker compose version >/dev/null
git --version >/dev/null
rg --version >/dev/null
make --version >/dev/null

echo "Toolchain check passed: Node $node_version, npm $npm_version, $python_version."
