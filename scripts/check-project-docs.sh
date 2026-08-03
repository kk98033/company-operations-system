#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

required_files=(
  "README.md"
  "01_公司流程與新版改進.md"
  "02_最終系統架構.md"
  "03_最終實作計畫.md"
  "04_開工前確認清單.md"
  "docs/需求追蹤矩陣.md"
  "docs/資料模型與業務規則.md"
  "docs/測試與驗收計畫.md"
  "docs/舊資料移轉計畫.md"
  "docs/本機開發與Git備份規範.md"
  "docs/風險與決策紀錄.md"
  "docs/progress/實作進度紀錄.md"
)

for relative_path in "${required_files[@]}"; do
  if [[ ! -s "$repo_root/$relative_path" ]]; then
    echo "Missing or empty required file: $relative_path" >&2
    exit 1
  fi
done

required_readme_sections=(
  "## 3. 強制執行規則"
  "## 4. 目前進度"
  "### 已完成"
  "### 進行中"
  "### 接下來要做"
  "## 6. Git 與備份規則"
)

for heading in "${required_readme_sections[@]}"; do
  if ! rg --fixed-strings --quiet "$heading" "$repo_root/README.md"; then
    echo "README is missing required section: $heading" >&2
    exit 1
  fi
done

if ! rg --fixed-strings --quiet "一次只進行一個小切片" "$repo_root/README.md"; then
  echo "README is missing the one-slice-at-a-time rule" >&2
  exit 1
fi

if ! rg --fixed-strings --quiet "每完成一個中型進度" "$repo_root/README.md"; then
  echo "README is missing the medium-checkpoint backup rule" >&2
  exit 1
fi

echo "Project documentation checks passed."
