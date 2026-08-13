#!/usr/bin/env python3
"""Build aggregate-only dry-run evidence for legacy pricing headers and details."""

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

HEADER_FIELDS = {"sal_da", "sno", "subpid", "pr_sum", "deliverid"}
ITEM_FIELDS = {"sal_da", "sno", "s_no", "contents", "amount", "sal_pr", "pr_tot"}


def _read(path: Path) -> tuple[bytes, list[str], list[dict[str, str]], int, int]:
    raw = path.read_bytes(); nul_count = raw.count(b"\0")
    text = raw.replace(b"\0", b"").decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = [row for row in reader if any((value or "").strip() for value in row.values() if value is not None)]
    return raw, reader.fieldnames or [], rows, nul_count, text.count("\ufffd")


def _decimal(value: str | None) -> Decimal | None:
    try: return Decimal((value or "").strip())
    except InvalidOperation: return None


def _key(row: dict[str, str]) -> tuple[str, str]:
    return (row.get("sal_da") or "").strip(), (row.get("sno") or "").strip()


def build_report(source_dir: Path) -> dict[str, Any]:
    header_raw, header_fields, headers, header_nuls, header_replacements = _read(source_dir / "sal.csv")
    item_raw, item_fields, items, item_nuls, item_replacements = _read(source_dir / "sal2.csv")
    _shipment_raw, _shipment_fields, shipments, _n1, _r1 = _read(source_dir / "subp_sale.csv")
    _order_raw, _order_fields, orders, _n2, _r2 = _read(source_dir / "subpoena.csv")
    header_keys = [_key(row) for row in headers]; item_keys = [_key(row) for row in items]
    header_set = set(header_keys); detail_counts = Counter(item_keys)
    shipment_ids = {(row.get("deliverid") or "").strip() for row in shipments}
    order_ids = {(row.get("id") or "").strip() for row in orders}
    invalid_amount = negative_amount = zero_amount = 0
    quantity_total = item_total = header_total = Decimal("0")
    for row in items:
        quantity, unit_price, subtotal = (_decimal(row.get(name)) for name in ("amount", "sal_pr", "pr_tot"))
        if quantity is None or unit_price is None or subtotal is None:
            invalid_amount += 1; continue
        if quantity < 0 or unit_price < 0 or subtotal < 0: negative_amount += 1
        if subtotal == 0: zero_amount += 1
        quantity_total += quantity; item_total += subtotal
    invalid_header_total = 0
    for row in headers:
        value = _decimal(row.get("pr_sum"))
        if value is None: invalid_header_total += 1
        else: header_total += value
    return {
        "schema_version": 1,
        "sources": {
            "headers": {"filename": "sal.csv", "sha256": hashlib.sha256(header_raw).hexdigest(), "data_rows": len(headers), "column_count": len(header_fields), "required_fields_present": HEADER_FIELDS.issubset(header_fields), "nul_bytes_sanitized": header_nuls, "replacement_characters": header_replacements},
            "items": {"filename": "sal2.csv", "sha256": hashlib.sha256(item_raw).hexdigest(), "data_rows": len(items), "column_count": len(item_fields), "required_fields_present": ITEM_FIELDS.issubset(item_fields), "nul_bytes_sanitized": item_nuls, "replacement_characters": item_replacements},
        },
        "counts": {
            "pricing_headers": len(headers), "pricing_items": len(items),
            "duplicate_header_keys": len(header_keys) - len(header_set),
            "headers_without_items": sum(key not in detail_counts for key in header_set),
            "empty_header_reference_items": sum(not all(key) for key in item_keys),
            "orphan_header_items": sum(all(key) and key not in header_set for key in item_keys),
            "matched_shipment_headers": sum((row.get("deliverid") or "").strip() in shipment_ids for row in headers),
            "empty_shipment_reference_headers": sum(not (row.get("deliverid") or "").strip() for row in headers),
            "orphan_shipment_headers": sum(bool((row.get("deliverid") or "").strip()) and (row.get("deliverid") or "").strip() not in shipment_ids for row in headers),
            "matched_work_order_headers": sum((row.get("subpid") or "").strip() in order_ids for row in headers),
            "invalid_amount_items": invalid_amount, "negative_amount_items": negative_amount,
            "zero_subtotal_items": zero_amount, "invalid_header_totals": invalid_header_total,
            "item_quantity_total": str(quantity_total), "item_subtotal_total": str(item_total),
            "header_total": str(header_total), "header_item_total_difference": str(header_total - item_total),
        },
        "mapping_policy": {
            "document_key": "sal.sal_da_plus_sno_to_legacy_source_key",
            "item_key": "sal2.sal_da_plus_sno_to_pricing_document",
            "shipment": "sal.deliverid_to_legacy_shipment_only_when_exact",
            "work_order": "sal.subpid_to_legacy_work_order_only_when_exact",
            "amounts": "preserve_legacy_quantity_unit_price_and_subtotal_without_repricing_spare",
            "text": "quarantine_replacement_characters_never_silently_delete",
            "orphan": "quarantine_never_guess_cross_document_links",
        },
        "privacy": "aggregate_only_no_customer_product_content_memo_or_row_values",
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
