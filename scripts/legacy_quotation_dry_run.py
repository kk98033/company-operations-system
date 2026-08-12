#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy quotation CSV files."""

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

HEADER = [
    "br_da",
    "br_no",
    "c_na",
    "br_mon",
    "br_pday",
    "br_tax",
    "used",
    "prt",
    "br_memo",
]
ITEM_HEADER = [
    "br_no",
    "sno",
    "prodna",
    "spec",
    "amt",
    "unit",
    "price",
    "cnt",
    "r_memo",
]
MONEY_FIELDS = ("amt", "price", "cnt")


def _read(path: Path) -> tuple[bytes, list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    reader = csv.DictReader(
        io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline="")
    )
    rows = [
        row
        for row in reader
        if any((value or "").strip() for value in row.values() if value is not None)
    ]
    return raw, reader.fieldnames or [], rows


def _numeric_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for field in MONEY_FIELDS:
        counts = Counter[str]()
        for row in rows:
            value = (row.get(field) or "").strip()
            if not value:
                counts["blank"] += 1
                continue
            try:
                parsed = Decimal(value.replace(",", ""))
            except InvalidOperation:
                counts["invalid"] += 1
            else:
                counts["negative" if parsed < 0 else "valid_nonnegative"] += 1
        result[field] = dict(sorted(counts.items()))
    return result


def build_report(source_dir: Path) -> dict[str, Any]:
    header_raw, header, headers = _read(source_dir / "b_replay1.csv")
    item_raw, item_header, items = _read(source_dir / "b_replay2.csv")
    document_keys = [(row.get("br_no") or "").strip() for row in headers]
    item_keys = [(row.get("br_no") or "").strip() for row in items]
    document_key_set = {key for key in document_keys if key}
    item_key_set = {key for key in item_keys if key}
    document_counts = Counter(document_keys)
    line_keys = Counter(
        ((row.get("br_no") or "").strip(), (row.get("sno") or "").strip())
        for row in items
    )
    return {
        "schema_version": 1,
        "sources": {
            "b_replay1": {
                "filename": "b_replay1.csv",
                "sha256": hashlib.sha256(header_raw).hexdigest(),
                "header_matches_expected": header == HEADER,
                "data_rows": len(headers),
            },
            "b_replay2": {
                "filename": "b_replay2.csv",
                "sha256": hashlib.sha256(item_raw).hexdigest(),
                "header_matches_expected": item_header == ITEM_HEADER,
                "data_rows": len(items),
            },
        },
        "counts": {
            "quotation_rows": len(headers),
            "quotation_item_rows": len(items),
            "empty_document_number": sum(not key for key in document_keys),
            "empty_item_document_number": sum(not key for key in item_keys),
            "duplicate_document_number_extra_rows": sum(
                count - 1 for key, count in document_counts.items() if key
            ),
            "duplicate_document_line_extra_rows": sum(
                count - 1 for count in line_keys.values()
            ),
            "orphan_item_rows": sum(
                bool(key) and key not in document_key_set for key in item_keys
            ),
            "quotations_without_items": len(document_key_set - item_key_set),
            "replacement_characters": sum(
                value.count("\ufffd")
                for row in [*headers, *items]
                for value in row.values()
                if value
            ),
        },
        "numeric_categories": _numeric_counts(items),
        "relationship_policy": "preserve_quotation_details_without_inventing_work_order_links",
        "privacy": "aggregate_only_no_customer_or_product_values",
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
    headers_ok = all(
        item["header_matches_expected"] for item in report["sources"].values()
    )
    return 0 if headers_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
