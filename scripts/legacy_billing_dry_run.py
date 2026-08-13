#!/usr/bin/env python3
"""Build aggregate-only legacy statement and receipt reconciliation evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SOURCES = {
    "rec": ("rec.csv", {"idno", "yrmn", "rec", "unrec"}, ("rec", "unrec")),
    "income": (
        "income.csv",
        {"income_da", "sno", "c_no", "yrmn", "unrec"},
        ("count1", "count2", "unrec"),
    ),
    "lsm": (
        "lsm.csv",
        {"yrmn", "c_no", "total", "tax", "suma"},
        ("total", "tax", "suma"),
    ),
    "rece": (
        "rece.csv",
        {"c_no", "yrmn", "rec_tot", "ptotal", "pay"},
        ("rec_tot", "ptotal", "pay"),
    ),
}


def _read(path: Path):
    raw = path.read_bytes()
    text = raw.replace(b"\0", b"").decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = [
        row
        for row in reader
        if any((value or "").strip() for value in row.values() if value is not None)
    ]
    return raw, reader.fieldnames or [], rows, raw.count(b"\0"), text.count("\ufffd")


def _decimal(value: str | None) -> Decimal | None:
    try:
        return Decimal((value or "").strip())
    except InvalidOperation:
        return None


def build_report(source_dir: Path) -> dict[str, Any]:
    source_report, counts, customer_month_keys = {}, {}, {}
    for name, (filename, required, amount_fields) in SOURCES.items():
        raw, fields, rows, nuls, replacements = _read(source_dir / filename)
        invalid = negative = 0
        totals = {field: Decimal("0") for field in amount_fields}
        keys = set()
        for row in rows:
            customer = (row.get("idno") or row.get("c_no") or "").strip()
            month = (row.get("yrmn") or "").strip()
            if customer and month:
                keys.add((customer, month))
            for field in amount_fields:
                value = _decimal(row.get(field))
                if value is None:
                    invalid += 1
                else:
                    totals[field] += value
                    if value < 0:
                        negative += 1
        customer_month_keys[name] = keys
        source_report[name] = {
            "filename": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "data_rows": len(rows),
            "column_count": len(fields),
            "required_fields_present": required.issubset(fields),
            "nul_bytes_sanitized": nuls,
            "replacement_characters": replacements,
        }
        counts[name] = {
            "rows": len(rows),
            "customer_month_keys": len(keys),
            "invalid_amount_values": invalid,
            "negative_amount_values": negative,
            "amount_totals": {key: str(value) for key, value in totals.items()},
        }
    counts["relations"] = {
        "income_keys_matching_rec": len(
            customer_month_keys["income"] & customer_month_keys["rec"]
        ),
        "lsm_keys_matching_rec": len(
            customer_month_keys["lsm"] & customer_month_keys["rec"]
        ),
        "rece_keys_matching_rec": len(
            customer_month_keys["rece"] & customer_month_keys["rec"]
        ),
        "income_keys_without_rec": len(
            customer_month_keys["income"] - customer_month_keys["rec"]
        ),
    }
    return {
        "schema_version": 1,
        "sources": source_report,
        "counts": counts,
        "mapping_policy": {
            "statement": "rec_or_lsm_customer_month_to_legacy_opening_statement_after_company_mapping",
            "receipt": "income_to_legacy_receipt_preserve_original_amounts_and_reference",
            "rece": "reconciliation_only_until_role_vs_rec_income_is_signed_off",
            "negative": "quarantine_or_opening_adjustment_never_silently_normalize",
            "orphan": "quarantine_never_guess_customer_or_month",
        },
        "privacy": "aggregate_only_no_customer_codes_bank_accounts_memos_or_row_values",
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
    print(
        json.dumps(
            {"counts": report["counts"], "apply_performed": False}, sort_keys=True
        )
    )
    return (
        0
        if all(
            source["required_fields_present"] for source in report["sources"].values()
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
