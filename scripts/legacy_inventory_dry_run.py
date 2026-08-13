#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy finished-goods inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "auto_id",
    "subpoenaid",
    "finishnumber",
    "delivernumber",
    "sparenumber",
}


def _read(path: Path) -> tuple[bytes, list[str], list[dict[str, str]], int]:
    raw = path.read_bytes()
    nul_count = raw.count(b"\0")
    text = raw.replace(b"\0", b"").decode("utf-8-sig", errors="strict")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = [
        row
        for row in reader
        if any((value or "").strip() for value in row.values() if value is not None)
    ]
    return raw, reader.fieldnames or [], rows, nul_count


def _decimal(value: str | None) -> Decimal | None:
    try:
        return Decimal((value or "").strip())
    except InvalidOperation:
        return None


def build_report(source_dir: Path) -> dict[str, Any]:
    merchandise_raw, fields, rows, nul_count = _read(source_dir / "merchandise.csv")
    _subpoena_raw, _subpoena_fields, work_orders, _ = _read(source_dir / "subpoena.csv")
    work_order_ids = {(row.get("id") or "").strip() for row in work_orders}
    work_order_date_prefixes = Counter(
        value[:8] for value in work_order_ids if len(value) >= 8
    )
    parent_ids = [(row.get("subpoenaid") or "").strip() for row in rows]
    parent_counts = Counter(value for value in parent_ids if value)
    balances: list[Decimal] = []
    invalid_quantity_rows = 0
    for row in rows:
        quantities = [
            _decimal(row.get("finishnumber")),
            _decimal(row.get("delivernumber")),
            _decimal(row.get("sparenumber")),
        ]
        if any(value is None for value in quantities):
            invalid_quantity_rows += 1
            continue
        finish, delivery, spare = quantities
        assert finish is not None and delivery is not None and spare is not None
        balances.append(finish - delivery - spare)
    return {
        "schema_version": 1,
        "source": {
            "filename": "merchandise.csv",
            "sha256": hashlib.sha256(merchandise_raw).hexdigest(),
            "data_rows": len(rows),
            "column_count": len(fields),
            "required_fields_present": REQUIRED_FIELDS.issubset(fields),
            "nul_bytes_sanitized": nul_count,
        },
        "counts": {
            "inventory_rows": len(rows),
            "empty_work_order_reference": sum(not value for value in parent_ids),
            "matched_work_order_rows": sum(value in work_order_ids for value in parent_ids),
            "orphan_work_order_rows": sum(
                bool(value) and value not in work_order_ids for value in parent_ids
            ),
            "date_prefix_single_candidate_rows": sum(
                work_order_date_prefixes[value] == 1 for value in parent_ids
            ),
            "date_prefix_ambiguous_candidate_rows": sum(
                work_order_date_prefixes[value] > 1 for value in parent_ids
            ),
            "duplicate_work_order_reference_extra_rows": sum(
                count - 1 for count in parent_counts.values()
            ),
            "invalid_quantity_rows": invalid_quantity_rows,
            "positive_balance_rows": sum(value > 0 for value in balances),
            "zero_balance_rows": sum(value == 0 for value in balances),
            "negative_balance_rows": sum(value < 0 for value in balances),
        },
        "mapping_policy": {
            "formula": "finishnumber - delivernumber - sparenumber",
            "target": "opening_final_completion_and_inventory_ledger_after_work_order_mapping",
            "legacy_reference": "preserve_subpoenaid_for_display_search_and_reconciliation",
            "date_prefix_candidate": "report_only_never_apply_without_a_unique_business_key",
            "negative_balance": "quarantine_never_create_negative_inventory",
        },
        "privacy": "aggregate_only_no_customer_product_or_row_values",
        "apply_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args()
    report = build_report(args.source_dir.resolve())
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"counts": report["counts"], "apply_performed": False}, sort_keys=True))
    return 0 if report["source"]["required_fields_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
