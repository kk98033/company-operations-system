#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy subpoena and quote work orders."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_SUBPOENA_FIELDS = {
    "id",
    "idbuffer",
    "customername",
    "ordername",
    "ordernumber",
    "deliverydate",
    "unitprice",
    "remark",
}
REQUIRED_QUOTE_FIELDS = {
    "auto_id",
    "subpoenaid",
    "oplatefactory",
    "bplatefactory",
    "oprintfactory",
    "bprintfactory",
    "odeliverfactory",
    "bdeliverfactory",
    "oremark",
}


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


def _source(
    raw: bytes, fields: list[str], rows: list[dict[str, str]], required: set[str]
) -> dict:
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data_rows": len(rows),
        "required_fields_present": required.issubset(fields),
        "column_count": len(fields),
    }


def build_report(source_dir: Path) -> dict[str, Any]:
    subpoena_raw, subpoena_fields, subpoenas = _read(source_dir / "subpoena.csv")
    quote_raw, quote_fields, quotes = _read(source_dir / "quote.csv")
    work_order_ids = [(row.get("id") or "").strip() for row in subpoenas]
    process_parent_ids = [(row.get("subpoenaid") or "").strip() for row in quotes]
    valid_ids = {value for value in work_order_ids if value}
    work_order_counts = Counter(value for value in work_order_ids if value)
    process_counts = Counter(value for value in process_parent_ids if value)
    return {
        "schema_version": 1,
        "sources": {
            "subpoena": {
                "filename": "subpoena.csv",
                **_source(
                    subpoena_raw,
                    subpoena_fields,
                    subpoenas,
                    REQUIRED_SUBPOENA_FIELDS,
                ),
            },
            "quote": {
                "filename": "quote.csv",
                **_source(quote_raw, quote_fields, quotes, REQUIRED_QUOTE_FIELDS),
            },
        },
        "counts": {
            "work_order_rows": len(subpoenas),
            "process_rows": len(quotes),
            "empty_work_order_id": sum(not value for value in work_order_ids),
            "duplicate_work_order_id_extra_rows": sum(
                count - 1 for count in work_order_counts.values()
            ),
            "empty_process_parent_id": sum(not value for value in process_parent_ids),
            "orphan_process_rows": sum(
                bool(value) and value not in valid_ids for value in process_parent_ids
            ),
            "work_orders_without_process_rows": sum(
                value not in process_counts for value in valid_ids
            ),
            "replacement_characters": sum(
                value.count("\ufffd")
                for row in [*subpoenas, *quotes]
                for value in row.values()
                if value
            ),
        },
        "mapping_policy": {
            "subpoena": "legacy_work_order_and_single_work_order_case",
            "quote": "legacy_process_details_only_not_new_quotation",
            "legacy_number": "preserve_original_id_and_idbuffer_for_display_and_search",
        },
        "privacy": "aggregate_only_no_customer_product_or_process_values",
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
    fields_ok = all(
        item["required_fields_present"] for item in report["sources"].values()
    )
    return 0 if fields_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
