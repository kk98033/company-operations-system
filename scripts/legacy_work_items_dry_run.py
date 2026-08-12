#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy wpa work items."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path


def _rows(path: Path) -> tuple[bytes, list[dict[str | None, str | None]]]:
    raw = path.read_bytes()
    rows = [row for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")) if any((value or "").strip() for value in row.values() if value is not None)]
    return raw, rows


def build_report(source_file: Path, customer_file: Path) -> dict:
    raw, rows = _rows(source_file)
    _, customers = _rows(customer_file)
    customer_codes = {(row.get("c_no") or "").strip().lower() for row in customers if (row.get("c_no") or "").strip()}
    keys = [((row.get("c_no") or "").strip().lower(), (row.get("wpano") or "").strip().lower()) for row in rows]
    key_counts = Counter(key for key in keys if all(key))
    return {
        "schema_version": 1,
        "source": {"filename": source_file.name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
        "counts": {
            "data_rows": len(rows),
            "empty_customer_code": sum(not key[0] for key in keys),
            "empty_work_item_code": sum(not key[1] for key in keys),
            "empty_name": sum(not (row.get("wpa_na") or "").strip() for row in rows),
            "orphan_customer_rows": sum(bool(key[0]) and key[0] not in customer_codes for key in keys),
            "duplicate_customer_item_extra_rows": sum(value - 1 for value in key_counts.values()),
            "replacement_characters": sum(value.count("\ufffd") for row in rows for value in row.values() if value),
            "row_width_mismatch": sum(None in row for row in rows),
        },
        "privacy": "aggregate_only_no_customer_or_work_item_values",
        "apply_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--customer-file", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()
    report = build_report(args.source_file.resolve(), args.customer_file.resolve())
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "apply_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
