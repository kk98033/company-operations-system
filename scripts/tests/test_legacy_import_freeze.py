from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from legacy_import_freeze import build_freeze_report, write_report  # noqa: E402


class LegacyImportFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_dir = self.root / "source"
        self.project_root = self.root / "project"
        self.source_dir.mkdir()
        (self.project_root / "scripts").mkdir(parents=True)
        (self.project_root / "scripts" / "reader.py").write_text("VERSION = 1\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_catalog(self, groups: list[dict[str, object]], expected: int = 2) -> Path:
        catalog_file = self.root / "catalog.json"
        catalog_file.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "catalog_version": "test-v1",
                    "source_system": "synthetic",
                    "expected_source_file_count": expected,
                    "program_files": ["scripts/reader.py"],
                    "table_groups": groups,
                }
            ),
            encoding="utf-8",
        )
        return catalog_file

    def write_sources(self) -> None:
        (self.source_dir / "cust.csv").write_text("id,name\n1,Sensitive Name\n", encoding="utf-8")
        (self.source_dir / "sysmeta.csv").write_text("id,value\n1,Secret Value\n", encoding="utf-8")

    def test_freezes_all_files_without_row_values_and_is_deterministic(self) -> None:
        self.write_sources()
        catalog = self.write_catalog(
            [
                {
                    "name": "customers",
                    "tables": ["cust"],
                    "disposition": "active_mapping_pending_approval",
                    "reason": "Synthetic customer mapping.",
                },
                {
                    "name": "metadata",
                    "patterns": ["sys*"],
                    "disposition": "excluded_non_business_metadata",
                    "reason": "Synthetic metadata exclusion.",
                },
            ]
        )

        first = build_freeze_report(self.source_dir, self.project_root, catalog, "a" * 40)
        second = build_freeze_report(self.source_dir, self.project_root, catalog, "a" * 40)

        self.assertEqual(first, second)
        self.assertEqual(first["summary"]["source_file_count"], 2)
        self.assertEqual(first["summary"]["classified_table_count"], 2)
        self.assertEqual(len(first["source_manifest_sha256"]), 64)
        self.assertEqual(len(first["importer_fingerprint_sha256"]), 64)
        serialized = json.dumps(first, ensure_ascii=False)
        self.assertNotIn("Sensitive Name", serialized)
        self.assertNotIn("Secret Value", serialized)

    def test_rejects_unmatched_or_multiply_classified_source_table(self) -> None:
        self.write_sources()
        unmatched = self.write_catalog(
            [{"name": "customers", "tables": ["cust"], "disposition": "active_mapping_pending_approval", "reason": "test"}]
        )
        with self.assertRaisesRegex(ValueError, "exactly one catalog group"):
            build_freeze_report(self.source_dir, self.project_root, unmatched, "b" * 40)

        overlapping = self.write_catalog(
            [
                {"name": "all", "patterns": ["*"], "disposition": "read_only_archive", "reason": "test"},
                {"name": "customers", "tables": ["cust"], "disposition": "active_mapping_pending_approval", "reason": "test"},
            ]
        )
        with self.assertRaisesRegex(ValueError, "exactly one catalog group"):
            build_freeze_report(self.source_dir, self.project_root, overlapping, "b" * 40)

    def test_rejects_source_count_drift_and_output_inside_source(self) -> None:
        self.write_sources()
        catalog = self.write_catalog(
            [{"name": "all", "patterns": ["*"], "disposition": "read_only_archive", "reason": "test"}],
            expected=3,
        )
        with self.assertRaisesRegex(ValueError, "Source file count"):
            build_freeze_report(self.source_dir, self.project_root, catalog, "c" * 40)

        with self.assertRaisesRegex(ValueError, "outside"):
            write_report({}, self.source_dir / "freeze.json", self.source_dir)


if __name__ == "__main__":
    unittest.main()
