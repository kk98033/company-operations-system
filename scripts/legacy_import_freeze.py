#!/usr/bin/env python3
"""Freeze the legacy source manifest and importer program fingerprint.

The generated report contains file identities, aggregate counts and mapping
classifications only. It never writes source row values into the report.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from legacy_import_profile import build_report, is_within


FREEZE_SCHEMA_VERSION = 1
FREEZE_TOOL_VERSION = "1.0.0"
ALLOWED_DISPOSITION_PREFIXES = (
    "active_",
    "active_or_archive_",
    "excluded_",
    "opening_",
    "read_only_",
)


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_catalog(catalog_file: Path) -> dict[str, Any]:
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "catalog_version",
        "source_system",
        "expected_source_file_count",
        "program_files",
        "table_groups",
    }
    if not isinstance(catalog, dict) or not required.issubset(catalog):
        raise ValueError("Import catalog is missing required fields.")
    if not isinstance(catalog["program_files"], list) or not catalog["program_files"]:
        raise ValueError("Import catalog must list program files.")
    if not isinstance(catalog["table_groups"], list) or not catalog["table_groups"]:
        raise ValueError("Import catalog must define table groups.")
    return catalog


def classify_tables(table_names: list[str], catalog: dict[str, Any]) -> list[dict[str, str]]:
    classified: list[dict[str, str]] = []
    for table_name in table_names:
        matches = []
        for group in catalog["table_groups"]:
            exact = table_name in group.get("tables", [])
            pattern = any(fnmatch.fnmatchcase(table_name, item) for item in group.get("patterns", []))
            if exact or pattern:
                matches.append(group)
        if len(matches) != 1:
            raise ValueError(
                f"Source table {table_name!r} must match exactly one catalog group; matched {len(matches)}."
            )
        group = matches[0]
        disposition = group.get("disposition", "")
        if not isinstance(disposition, str) or not disposition.startswith(ALLOWED_DISPOSITION_PREFIXES):
            raise ValueError(f"Catalog group {group.get('name')!r} has an invalid disposition.")
        classified.append(
            {
                "source_table": table_name,
                "group": group["name"],
                "disposition": disposition,
                "reason": group["reason"],
            }
        )
    return classified


def program_fingerprint(project_root: Path, program_files: list[str]) -> tuple[list[dict[str, Any]], str]:
    entries = []
    for relative_path in sorted(program_files):
        program_file = (project_root / relative_path).resolve()
        if not is_within(program_file, project_root.resolve()) or not program_file.is_file():
            raise ValueError(f"Importer program file is missing or outside the project: {relative_path}")
        entries.append(
            {
                "relative_path": relative_path,
                "size_bytes": program_file.stat().st_size,
                "sha256": hashlib.sha256(program_file.read_bytes()).hexdigest(),
            }
        )
    return entries, canonical_sha256(entries)


def build_freeze_report(
    source_dir: Path,
    project_root: Path,
    catalog_file: Path,
    repository_commit: str,
) -> dict[str, Any]:
    catalog = load_catalog(catalog_file)
    profile = build_report(source_dir)
    if profile["source_file_count"] != catalog["expected_source_file_count"]:
        raise ValueError(
            "Source file count does not match the frozen catalog: "
            f"expected {catalog['expected_source_file_count']}, got {profile['source_file_count']}."
        )

    table_names = [Path(table["relative_path"]).stem for table in profile["tables"]]
    if len(set(table_names)) != len(table_names):
        raise ValueError("Source table names must be unique across the manifest.")
    classifications = classify_tables(table_names, catalog)
    classifications_by_table = {item["source_table"]: item for item in classifications}

    manifest_files = []
    for table in profile["tables"]:
        table_name = Path(table["relative_path"]).stem
        manifest_files.append(
            {
                "relative_path": table["relative_path"],
                "source_table": table_name,
                "content_sha256": table["sha256"],
                "size_bytes": table["size_bytes"],
                "physical_line_count": table["physical_lines"],
                "logical_row_count_including_header": table["logical_rows_including_header"],
                "data_row_count": table["data_rows"],
                "valid_utf8": table["valid_utf8"],
                "csv_error_line": table["csv_error_line"],
                "row_width_mismatch_count": table["row_width_mismatch_count"],
                "replacement_character_count": table["replacement_character_count"],
                "control_character_count": table["control_character_count"],
                "classification": classifications_by_table[table_name],
            }
        )

    source_manifest = {
        "source_system": catalog["source_system"],
        "files": manifest_files,
    }
    programs, importer_fingerprint = program_fingerprint(project_root, catalog["program_files"])
    disposition_counts = Counter(item["disposition"] for item in classifications)
    group_counts = Counter(item["group"] for item in classifications)
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "tool_version": FREEZE_TOOL_VERSION,
        "catalog_version": catalog["catalog_version"],
        "source_system": catalog["source_system"],
        "repository_commit": repository_commit,
        "source_manifest_sha256": canonical_sha256(source_manifest),
        "importer_fingerprint_sha256": importer_fingerprint,
        "summary": {
            "source_file_count": len(manifest_files),
            "source_data_row_count": sum(item["data_row_count"] for item in manifest_files),
            "source_size_bytes": sum(item["size_bytes"] for item in manifest_files),
            "classified_table_count": len(classifications),
            "group_counts": dict(sorted(group_counts.items())),
            "disposition_counts": dict(sorted(disposition_counts.items())),
            "profile_anomalies": profile["summary"],
        },
        "program_files": programs,
        "source_files": manifest_files,
    }


def repository_commit_for_clean_programs(project_root: Path, program_files: list[str]) -> str:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *program_files],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip():
        raise ValueError("Importer program files must be committed before creating the freeze report.")
    return commit


def write_report(report: dict[str, Any], output_file: Path, source_dir: Path) -> None:
    output_file = output_file.resolve()
    source_dir = source_dir.resolve()
    if output_file == source_dir or is_within(output_file, source_dir):
        raise ValueError("Freeze report must be written outside the read-only source directory.")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    parser.add_argument(
        "--catalog-file",
        default=Path("config/import/legacy_uv_print_catalog.json"),
        type=Path,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    source_dir = args.source_dir.resolve()
    catalog_file = (project_root / args.catalog_file).resolve()
    if not source_dir.is_dir():
        raise SystemExit("Legacy source directory does not exist.")
    try:
        catalog = load_catalog(catalog_file)
        commit = repository_commit_for_clean_programs(project_root, catalog["program_files"])
        report = build_freeze_report(source_dir, project_root, catalog_file, commit)
        write_report(report, args.output_file, source_dir)
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise SystemExit(f"Import freeze failed: {error}") from None
    print(f"Frozen {report['summary']['source_file_count']} source files.")
    print(f"Source manifest SHA-256: {report['source_manifest_sha256']}")
    print(f"Importer fingerprint SHA-256: {report['importer_fingerprint_sha256']}")
    print(f"Repository commit: {report['repository_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
