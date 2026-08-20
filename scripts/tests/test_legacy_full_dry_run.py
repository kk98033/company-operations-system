from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import legacy_full_dry_run as full  # noqa: E402


class LegacyFullDryRunTests(unittest.TestCase):
    def test_verifies_frozen_files_and_never_applies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            for table in sorted(set().union(*full.PROCESSED_TABLES.values())):
                (source / f"{table}.csv").write_text("id,value\n1,private\n", encoding="utf-8")
            frozen_files = []
            for source_file in sorted(source.glob("*.csv")):
                frozen_files.append(
                    {
                        "relative_path": source_file.name,
                        "source_table": source_file.stem,
                        "content_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
                        "classification": {
                            "disposition": "active_mapping_pending_approval"
                        },
                    }
                )
            freeze = {
                "source_manifest_sha256": "a" * 64,
                "importer_fingerprint_sha256": "b" * 64,
                "repository_commit": "c" * 40,
                "summary": {
                    "source_data_row_count": len(frozen_files),
                    "profile_anomalies": {"replacement_characters": 0},
                },
                "source_files": frozen_files,
            }
            builders = {
                name: (lambda _source, domain=name: {
                    "counts": {}, "domain": domain, "apply_performed": False
                })
                for name in full.PROCESSED_TABLES
            }

            report = full.build_full_report(source, freeze, domain_builders=builders)

            self.assertFalse(report["apply_performed"])
            self.assertFalse(report["ready_for_apply"])
            self.assertEqual(report["summary"]["manifest_only_table_count"], 0)
            self.assertEqual(set(report["domain_reports"]), set(full.PROCESSED_TABLES))
            self.assertNotIn("private", str(report))

            changed = source / frozen_files[0]["relative_path"]
            changed.write_text("id,value\n1,changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash differs"):
                full.build_full_report(source, freeze, domain_builders=builders)

    def test_rejects_missing_domain_builder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            source_file = source / "cust.csv"
            source_file.write_text("id,value\n", encoding="utf-8")
            freeze = {
                "source_manifest_sha256": "a" * 64,
                "importer_fingerprint_sha256": "b" * 64,
                "repository_commit": "c" * 40,
                "summary": {"source_data_row_count": 0, "profile_anomalies": {}},
                "source_files": [{
                    "relative_path": "cust.csv",
                    "source_table": "cust",
                    "content_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
                    "classification": {"disposition": "active_mapping_pending_approval"},
                }],
            }
            with self.assertRaisesRegex(ValueError, "builders"):
                full.build_full_report(source, freeze, domain_builders={})


if __name__ == "__main__":
    unittest.main()
