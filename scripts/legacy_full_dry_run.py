#!/usr/bin/env python3
"""Run every aggregate-only legacy domain audit under one frozen manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import legacy_billing_dry_run
import legacy_customer_dry_run
import legacy_inventory_dry_run
import legacy_master_data_dry_run
import legacy_pricing_dry_run
import legacy_quotation_dry_run
import legacy_shipment_dry_run
import legacy_work_items_dry_run
import legacy_work_order_dry_run


FULL_DRY_RUN_SCHEMA_VERSION = 1
FULL_DRY_RUN_TOOL_VERSION = "1.0.0"

PROCESSED_TABLES = {
    "billing": {"income", "lsm", "rec", "rece"},
    "customers": {"cust"},
    "inventory": {"merchandise"},
    "master_data": {"fact", "fno_set", "gloss", "paste", "qly_set"},
    "pricing": {"sal", "sal2"},
    "quotations": {"b_replay1", "b_replay2"},
    "shipments": {"subp_sale", "subp_sale2"},
    "work_items": {"wpa"},
    "work_orders_current": {"quote", "subpoena"},
    "work_orders_history": {"quote_his", "subpoena_his"},
}


def _history_work_order_report(source_dir: Path) -> dict[str, Any]:
    def read(name: str) -> tuple[bytes, list[dict[str, str]]]:
        raw = (source_dir / f"{name}.csv").read_bytes()
        reader = csv.DictReader(
            io.StringIO(raw.replace(b"\0", b"").decode("utf-8-sig", errors="replace"), newline="")
        )
        rows = [
            row
            for row in reader
            if any((value or "").strip() for value in row.values() if value is not None)
        ]
        return raw, rows

    order_raw, orders = read("subpoena_his")
    process_raw, processes = read("quote_his")
    order_ids = [(row.get("id") or "").strip() for row in orders]
    parent_ids = [(row.get("subpoenaid") or "").strip() for row in processes]
    valid_ids = {value for value in order_ids if value}
    order_counts = Counter(value for value in order_ids if value)
    process_counts = Counter(value for value in parent_ids if value)
    return {
        "schema_version": 1,
        "sources": {
            "subpoena_his": {
                "filename": "subpoena_his.csv",
                "sha256": hashlib.sha256(order_raw).hexdigest(),
                "data_rows": len(orders),
            },
            "quote_his": {
                "filename": "quote_his.csv",
                "sha256": hashlib.sha256(process_raw).hexdigest(),
                "data_rows": len(processes),
            },
        },
        "counts": {
            "work_order_rows": len(orders),
            "process_rows": len(processes),
            "empty_work_order_id": sum(not value for value in order_ids),
            "duplicate_work_order_id_extra_rows": sum(
                count - 1 for count in order_counts.values()
            ),
            "empty_process_parent_id": sum(not value for value in parent_ids),
            "orphan_process_rows": sum(
                bool(value) and value not in valid_ids for value in parent_ids
            ),
            "work_orders_without_process_rows": sum(
                value not in process_counts for value in valid_ids
            ),
        },
        "mapping_policy": {
            "history": "preserve_legacy_numbers_and_archive_state",
            "orphan": "quarantine_never_guess_parent_relationship",
        },
        "privacy": "aggregate_only_no_customer_product_or_process_values",
        "apply_performed": False,
    }


def default_domain_builders() -> dict[str, Callable[[Path], dict[str, Any]]]:
    return {
        "customers": lambda source: legacy_customer_dry_run.build_customer_report(source / "cust.csv"),
        "master_data": legacy_master_data_dry_run.build_report,
        "work_items": lambda source: legacy_work_items_dry_run.build_report(
            source / "wpa.csv", source / "cust.csv"
        ),
        "quotations": legacy_quotation_dry_run.build_report,
        "work_orders_current": legacy_work_order_dry_run.build_report,
        "work_orders_history": _history_work_order_report,
        "inventory": legacy_inventory_dry_run.build_report,
        "shipments": legacy_shipment_dry_run.build_report,
        "pricing": legacy_pricing_dry_run.build_report,
        "billing": legacy_billing_dry_run.build_report,
    }


def verify_frozen_sources(source_dir: Path, freeze_report: dict[str, Any]) -> None:
    frozen_files = freeze_report.get("source_files")
    if not isinstance(frozen_files, list) or not frozen_files:
        raise ValueError("Freeze report does not contain source files.")
    actual_csv = {
        path.relative_to(source_dir).as_posix()
        for path in source_dir.rglob("*.csv")
        if path.is_file() and not path.is_symlink()
    }
    expected_csv = {item["relative_path"] for item in frozen_files}
    if actual_csv != expected_csv:
        raise ValueError("Legacy source file set differs from the frozen manifest.")
    for item in frozen_files:
        source_file = source_dir / item["relative_path"]
        if hashlib.sha256(source_file.read_bytes()).hexdigest() != item["content_sha256"]:
            raise ValueError(f"Legacy source hash differs from freeze: {item['relative_path']}")


def _blockers(
    domain_reports: dict[str, dict[str, Any]],
    freeze_report: dict[str, Any],
    manifest_only_active: list[str],
) -> list[dict[str, Any]]:
    counts = {name: report.get("counts", {}) for name, report in domain_reports.items()}
    candidates = {
        "SOURCE_TEXT_REPAIR_REQUIRED": freeze_report["summary"]["profile_anomalies"].get(
            "replacement_characters", 0
        ),
        "WORK_ITEM_CUSTOMER_ORPHANS": counts["work_items"].get("orphan_customer_rows", 0),
        "QUOTATION_ITEM_ORPHANS": counts["quotations"].get("orphan_item_rows", 0),
        "CURRENT_PROCESS_ORPHANS": counts["work_orders_current"].get("orphan_process_rows", 0),
        "HISTORY_PROCESS_ORPHANS": counts["work_orders_history"].get("orphan_process_rows", 0),
        "INVENTORY_WORK_ORDER_ORPHANS": counts["inventory"].get("orphan_work_order_rows", 0),
        "SHIPMENT_HEADER_ORPHANS": counts["shipments"].get("orphan_header_items", 0),
        "SHIPMENT_WORK_ORDER_ORPHANS": counts["shipments"].get("orphan_work_order_items", 0),
        "PRICING_HEADER_ORPHANS": counts["pricing"].get("orphan_header_items", 0),
        "PRICING_SHIPMENT_ORPHANS": counts["pricing"].get("orphan_shipment_headers", 0),
        "BILLING_UNMATCHED_INCOME": counts["billing"].get("relations", {}).get(
            "income_keys_without_rec", 0
        ),
        "ACTIVE_TABLES_MANIFEST_ONLY": len(manifest_only_active),
    }
    return [
        {"code": code, "count": count, "severity": "high"}
        for code, count in candidates.items()
        if count
    ]


def build_full_report(
    source_dir: Path,
    freeze_report: dict[str, Any],
    *,
    domain_builders: dict[str, Callable[[Path], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    verify_frozen_sources(source_dir, freeze_report)
    builders = domain_builders if domain_builders is not None else default_domain_builders()
    if set(builders) != set(PROCESSED_TABLES):
        raise ValueError("Full dry-run builders do not match the frozen domain contract.")
    reports = {name: builders[name](source_dir) for name in sorted(builders)}
    if any(report.get("apply_performed") is not False for report in reports.values()):
        raise ValueError("Every domain report must remain aggregate-only with apply disabled.")

    processed = set().union(*PROCESSED_TABLES.values())
    source_files = freeze_report["source_files"]
    manifest_only = [item for item in source_files if item["source_table"] not in processed]
    manifest_only_active = sorted(
        item["source_table"]
        for item in manifest_only
        if not item["classification"]["disposition"].startswith(("excluded_", "read_only_"))
    )
    blockers = _blockers(reports, freeze_report, manifest_only_active)
    return {
        "schema_version": FULL_DRY_RUN_SCHEMA_VERSION,
        "tool_version": FULL_DRY_RUN_TOOL_VERSION,
        "source_manifest_sha256": freeze_report["source_manifest_sha256"],
        "importer_fingerprint_sha256": freeze_report["importer_fingerprint_sha256"],
        "frozen_repository_commit": freeze_report["repository_commit"],
        "summary": {
            "source_file_count": len(source_files),
            "source_data_row_count": freeze_report["summary"]["source_data_row_count"],
            "aggregate_dry_run_table_count": len(processed),
            "manifest_only_table_count": len(manifest_only),
            "manifest_only_active_table_count": len(manifest_only_active),
            "high_risk_blocker_count": len(blockers),
        },
        "domain_reports": reports,
        "manifest_only_active_tables": manifest_only_active,
        "high_risk_blockers": blockers,
        "ready_for_apply": False,
        "apply_performed": False,
        "privacy": "aggregate_only_no_source_row_values",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--freeze-report", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        freeze_report = json.loads(args.freeze_report.read_text(encoding="utf-8"))
        report = build_full_report(args.source_dir, freeze_report)
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"Full dry-run failed: {error}") from None
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
