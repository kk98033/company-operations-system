import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "legacy_quotation_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_quotation_dry_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LegacyQuotationDryRunTests(unittest.TestCase):
    def test_report_is_aggregate_only_and_detects_orphans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            with (source / "b_replay1.csv").open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=MODULE.HEADER)
                writer.writeheader()
                writer.writerow({"br_no": "SYN-Q-1", "c_na": "Synthetic Customer"})
            with (source / "b_replay2.csv").open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=MODULE.ITEM_HEADER)
                writer.writeheader()
                writer.writerow(
                    {
                        "br_no": "SYN-Q-1",
                        "sno": "1",
                        "prodna": "Synthetic A",
                        "amt": "2",
                        "price": "1.25",
                        "cnt": "2.50",
                    }
                )
                writer.writerow(
                    {
                        "br_no": "MISSING",
                        "sno": "1",
                        "prodna": "Synthetic B",
                        "amt": "bad",
                    }
                )
            report = MODULE.build_report(source)
            self.assertEqual(report, MODULE.build_report(source))
            self.assertEqual(report["counts"]["quotation_rows"], 1)
            self.assertEqual(report["counts"]["quotation_item_rows"], 2)
            self.assertEqual(report["counts"]["orphan_item_rows"], 1)
            self.assertEqual(report["numeric_categories"]["amt"]["invalid"], 1)
            self.assertFalse(report["apply_performed"])
            serialized = str(report)
            self.assertNotIn("Synthetic Customer", serialized)
            self.assertNotIn("Synthetic A", serialized)


if __name__ == "__main__":
    unittest.main()
