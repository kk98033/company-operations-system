#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <checkpoint-name>" >&2
  exit 2
fi

checkpoint_name="$1"
if [[ ! "$checkpoint_name" =~ ^[a-z0-9][a-z0-9._-]*$ ]]; then
  echo "Checkpoint name must use lowercase letters, numbers, dot, underscore or dash." >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
cd "$repo_root"

git rev-parse --is-inside-work-tree >/dev/null

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Update README/progress, commit, then retry." >&2
  exit 1
fi

tag_name="checkpoint-$checkpoint_name"
if git rev-parse --verify --quiet "refs/tags/$tag_name" >/dev/null; then
  echo "Tag already exists: $tag_name" >&2
  exit 1
fi

timestamp="$(date '+%Y%m%d-%H%M%S')"
backup_dir="$repo_root/../git-backups"
bundle_path="$backup_dir/company-system-$checkpoint_name-$timestamp.bundle"
mkdir -p "$backup_dir"

git tag -a "$tag_name" -m "Checkpoint $checkpoint_name"
git bundle create "$bundle_path" --all
git bundle verify "$bundle_path"

if git remote get-url origin >/dev/null 2>&1; then
  current_branch="$(git branch --show-current)"
  if [[ -z "$current_branch" ]]; then
    echo "Cannot push from detached HEAD." >&2
    exit 1
  fi
  git push origin "$current_branch"
  git push origin "$tag_name"
  echo "Remote branch and tag pushed to origin."
else
  echo "WARNING: origin is not configured; this is not an off-device backup." >&2
fi

echo "Created tag: $tag_name"
echo "Created and verified bundle: $bundle_path"
