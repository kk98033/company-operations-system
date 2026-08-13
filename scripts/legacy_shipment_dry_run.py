#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy shipment headers and details."""

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

HEADER_FIELDS = {"saledate", "deliverid", "customername", "deliverrows", "remark"}
ITEM_FIELDS = {"deliverid", "deliversn", "delivernumber", "sparenumber", "subpoenaid", "tr_ok"}


def _read(path: Path) -> tuple[bytes, list[str], list[dict[str, str]], int]:
    raw = path.read_bytes(); nul_count = raw.count(b"\0")
    reader = csv.DictReader(io.StringIO(raw.replace(b"\0", b"").decode("utf-8-sig"), newline=""))
    rows = [row for row in reader if any((value or "").strip() for value in row.values() if value is not None)]
    return raw, reader.fieldnames or [], rows, nul_count


def _quantity(value: str | None) -> Decimal | None:
    try: return Decimal((value or "").strip())
    except InvalidOperation: return None


def build_report(source_dir: Path) -> dict[str, Any]:
    header_raw, header_fields, headers, header_nuls = _read(source_dir / "subp_sale.csv")
    item_raw, item_fields, items, item_nuls = _read(source_dir / "subp_sale2.csv")
    _order_raw, _order_fields, orders, _order_nuls = _read(source_dir / "subpoena.csv")
    header_ids = {(row.get("deliverid") or "").strip() for row in headers}
    order_ids = {(row.get("id") or "").strip() for row in orders}
    item_header_ids = [(row.get("deliverid") or "").strip() for row in items]
    item_order_ids = [(row.get("subpoenaid") or "").strip() for row in items]
    invalid_quantity = negative_quantity = zero_total = 0
    delivered_total = spare_total = Decimal("0")
    for row in items:
        delivered, spare = _quantity(row.get("delivernumber")), _quantity(row.get("sparenumber"))
        if delivered is None or spare is None:
            invalid_quantity += 1; continue
        if delivered < 0 or spare < 0: negative_quantity += 1
        if delivered + spare == 0: zero_total += 1
        delivered_total += delivered; spare_total += spare
    detail_counts = Counter(value for value in item_header_ids if value)
    return {
        "schema_version": 1,
        "sources": {
            "headers": {"filename": "subp_sale.csv", "sha256": hashlib.sha256(header_raw).hexdigest(), "data_rows": len(headers), "column_count": len(header_fields), "required_fields_present": HEADER_FIELDS.issubset(header_fields), "nul_bytes_sanitized": header_nuls},
            "items": {"filename": "subp_sale2.csv", "sha256": hashlib.sha256(item_raw).hexdigest(), "data_rows": len(items), "column_count": len(item_fields), "required_fields_present": ITEM_FIELDS.issubset(item_fields), "nul_bytes_sanitized": item_nuls},
        },
        "counts": {
            "shipment_headers": len(headers), "shipment_items": len(items),
            "headers_without_items": sum(value not in detail_counts for value in header_ids),
            "empty_header_reference_items": sum(not value for value in item_header_ids),
            "orphan_header_items": sum(bool(value) and value not in header_ids for value in item_header_ids),
            "matched_work_order_items": sum(value in order_ids for value in item_order_ids),
            "empty_work_order_reference_items": sum(not value for value in item_order_ids),
            "orphan_work_order_items": sum(bool(value) and value not in order_ids for value in item_order_ids),
            "invalid_quantity_items": invalid_quantity, "negative_quantity_items": negative_quantity,
            "zero_delivery_total_items": zero_total,
            "delivered_quantity_total": str(delivered_total), "spare_quantity_total": str(spare_total),
        },
        "mapping_policy": {
            "header": "subp_sale.deliverid_to_shipments_legacy_source_key",
            "item": "subp_sale2.deliverid_to_shipment_and_subpoenaid_to_work_order",
            "quantity": "preserve_delivernumber_and_sparenumber_separately",
            "legacy_number": "preserve_deliverid_without_adding_new_prefix",
            "orphan": "quarantine_never_guess_cross_document_links",
        },
        "privacy": "aggregate_only_no_customer_product_address_remark_or_row_values",
        "apply_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path); parser.add_argument("--output-file", required=True, type=Path)
    args = parser.parse_args(); report = build_report(args.source_dir.resolve())
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "apply_performed": False}, sort_keys=True))
    return 0 if all(source["required_fields_present"] for source in report["sources"].values()) else 1


if __name__ == "__main__": raise SystemExit(main())
