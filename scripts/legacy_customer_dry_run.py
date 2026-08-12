#!/usr/bin/env python3
"""Build a deterministic aggregate-only dry-run report for legacy cust.csv."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
EXPECTED_HEADER = [
    "c_no", "c_name", "c_sno", "c_mailno", "c_city", "c_addr", "c_tel",
    "c_fax", "c_bbcall", "c_acttel", "c_man", "c_conn", "c_tel2", "c_na",
    "c_tax", "bpoint",
]


def _category(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return "blank"
    if normalized in {"0", "false", "no", "n"}:
        return "zero_or_false"
    if normalized in {"1", "true", "yes", "y"}:
        return "one_or_true"
    return "other"


def build_customer_report(source_file: Path) -> dict[str, Any]:
    raw = source_file.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    header = reader.fieldnames or []
    rows = [
        row for row in reader
        if any((value or "").strip() for value in row.values() if value is not None)
    ]
    codes = [row.get("c_no", "").strip() for row in rows]
    code_counts = Counter(code.lower() for code in codes if code)
    replacement_count = sum(
        value.count("\ufffd") for row in rows for value in row.values() if value
    )
    nonempty_fields = {
        field: sum(bool((row.get(field) or "").strip()) for row in rows)
        for field in EXPECTED_HEADER
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "filename": source_file.name,
            "sha256": digest,
            "size_bytes": len(raw),
        },
        "header": {
            "matches_expected": header == EXPECTED_HEADER,
            "missing": sorted(set(EXPECTED_HEADER) - set(header)),
            "unexpected": sorted(set(header) - set(EXPECTED_HEADER)),
        },
        "counts": {
            "data_rows": len(rows),
            "empty_code": sum(not code for code in codes),
            "empty_name": sum(not (row.get("c_name") or "").strip() for row in rows),
            "unique_normalized_codes": len(code_counts),
            "duplicate_code_extra_rows": sum(count - 1 for count in code_counts.values()),
            "row_width_mismatch": sum(None in row for row in rows),
            "replacement_characters": replacement_count,
        },
        "legacy_billing_categories": {
            "c_tax": dict(sorted(Counter(_category(row.get("c_tax", "")) for row in rows).items())),
            "bpoint": dict(sorted(Counter(_category(row.get("bpoint", "")) for row in rows).items())),
        },
        "mapped_field_nonempty_counts": nonempty_fields,
        "privacy": "aggregate_only_no_customer_values",
        "apply_performed": False,
    }


def write_report(report: dict[str, Any], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()
    source = args.source_file.resolve()
    output = args.output_file.resolve()
    if not source.is_file() or source.is_symlink():
        raise SystemExit("Source must be an existing regular file.")
    if source == output:
        raise SystemExit("Output must not overwrite the source file.")
    report = build_customer_report(source)
    write_report(report, output)
    print(json.dumps({"counts": report["counts"], "apply_performed": False}, sort_keys=True))
    return 0 if report["header"]["matches_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
