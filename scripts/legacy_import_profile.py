#!/usr/bin/env python3
"""Create a deterministic, non-PII profile of legacy CSV sources.

The source directory is opened read-only. Reports contain filenames, hashes,
headers, and aggregate counts only; no customer or business row values are
written to the output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


TOOL_VERSION = "1.0.0"


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def hash_and_physical_lines(source_file: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    newline_count = 0
    final_byte = b""

    with source_file.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            newline_count += chunk.count(b"\n")
            final_byte = chunk[-1:]

    physical_lines = newline_count + (1 if source_file.stat().st_size and final_byte != b"\n" else 0)
    return digest.hexdigest(), source_file.stat().st_size, physical_lines


def profile_csv(source_file: Path, source_root: Path) -> dict[str, Any]:
    sha256, size_bytes, physical_lines = hash_and_physical_lines(source_file)
    profile: dict[str, Any] = {
        "relative_path": source_file.relative_to(source_root).as_posix(),
        "size_bytes": size_bytes,
        "sha256": sha256,
        "physical_lines": physical_lines,
        "valid_utf8": True,
        "csv_error_line": None,
        "header": [],
        "header_column_count": 0,
        "logical_rows_including_header": 0,
        "data_rows": 0,
        "empty_rows": 0,
        "row_width_mismatch_count": 0,
        "empty_first_key_count": 0,
        "unique_first_key_count": 0,
        "duplicate_first_key_extra_count": 0,
        "replacement_character_count": 0,
        "control_character_count": 0,
        "control_character_codepoints": {},
    }

    first_keys: set[str] = set()

    try:
        with source_file.open("r", encoding="utf-8-sig", errors="strict", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                return profile

            profile["header"] = header
            profile["header_column_count"] = len(header)
            profile["logical_rows_including_header"] = 1

            for row in reader:
                profile["logical_rows_including_header"] += 1
                if not row or all(cell == "" for cell in row):
                    profile["empty_rows"] += 1
                    continue

                profile["data_rows"] += 1
                if len(row) != len(header):
                    profile["row_width_mismatch_count"] += 1

                first_key = row[0].strip() if row else ""
                if not first_key:
                    profile["empty_first_key_count"] += 1
                elif first_key in first_keys:
                    profile["duplicate_first_key_extra_count"] += 1
                else:
                    first_keys.add(first_key)

                for cell in row:
                    profile["replacement_character_count"] += cell.count("\ufffd")
                    for character in cell:
                        if ord(character) < 32 and character not in "\t\r\n":
                            profile["control_character_count"] += 1
                            codepoint = f"U+{ord(character):04X}"
                            profile["control_character_codepoints"][codepoint] = (
                                profile["control_character_codepoints"].get(codepoint, 0) + 1
                            )

            profile["unique_first_key_count"] = len(first_keys)
    except UnicodeDecodeError:
        profile["valid_utf8"] = False
    except csv.Error:
        profile["csv_error_line"] = getattr(reader, "line_num", None)

    return profile


def build_report(source_dir: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    csv_files = sorted(
        source_file
        for source_file in source_dir.rglob("*.csv")
        if source_file.is_file() and not source_file.is_symlink()
    )
    tables = [profile_csv(source_file, source_dir) for source_file in csv_files]

    return {
        "schema_version": 1,
        "tool_version": TOOL_VERSION,
        "source_file_count": len(tables),
        "summary": {
            "invalid_utf8_files": sum(not table["valid_utf8"] for table in tables),
            "csv_error_files": sum(table["csv_error_line"] is not None for table in tables),
            "row_width_mismatches": sum(table["row_width_mismatch_count"] for table in tables),
            "empty_first_keys": sum(table["empty_first_key_count"] for table in tables),
            "replacement_characters": sum(table["replacement_character_count"] for table in tables),
            "control_characters": sum(table["control_character_count"] for table in tables),
        },
        "tables": tables,
    }


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "legacy_source_profile.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status for invalid UTF-8, CSV errors, or row-width mismatches.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not source_dir.is_dir():
        raise SystemExit(f"Source directory does not exist: {source_dir}")
    if output_dir == source_dir or is_within(output_dir, source_dir):
        raise SystemExit("Output directory must be outside the read-only source directory.")

    report = build_report(source_dir)
    report_path = write_report(report, output_dir)
    print(f"Profiled {report['source_file_count']} CSV files.")
    print(f"Report: {report_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))

    if args.strict and (
        report["summary"]["invalid_utf8_files"]
        or report["summary"]["csv_error_files"]
        or report["summary"]["row_width_mismatches"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
