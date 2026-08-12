#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy master-data CSV files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

SOURCES = {
    "vendors": ("fact.csv", "f_no", "f_name"),
    "paper_types": ("qly_set.csv", "q_no", "q_na"),
    "paper_mills": ("fno_set.csv", "f_no", "f_na"),
    "coatings": ("gloss.csv", "fg_no", "fgname"),
    "adhesives": ("paste.csv", "fp_no", "fpastename"),
}


def _profile(path: Path, code_field: str, name_field: str) -> dict:
    raw = path.read_bytes()
    rows = [row for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")) if any((value or "").strip() for value in row.values() if value is not None)]
    codes = [(row.get(code_field) or "").strip().lower() for row in rows]
    counts = Counter(code for code in codes if code)
    return {
        "filename": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data_rows": len(rows),
        "empty_code": sum(not code for code in codes),
        "empty_name": sum(not (row.get(name_field) or "").strip() for row in rows),
        "duplicate_code_extra_rows": sum(value - 1 for value in counts.values()),
        "replacement_characters": sum(value.count("\ufffd") for row in rows for value in row.values() if value),
        "row_width_mismatch": sum(None in row for row in rows),
    }


def build_report(source_dir: Path) -> dict:
    return {
        "schema_version": 1,
        "sources": {key: _profile(source_dir / filename, code, name) for key, (filename, code, name) in SOURCES.items()},
        "confirmed_process_count": 13,
        "privacy": "aggregate_only_no_master_values",
        "apply_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()
    report = build_report(args.source_dir.resolve())
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": {key: value["data_rows"] for key, value in report["sources"].items()}, "apply_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
