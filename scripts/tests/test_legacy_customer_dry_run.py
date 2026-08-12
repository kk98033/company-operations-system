import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "legacy_customer_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_customer_dry_run", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EXPECTED_HEADER = MODULE.EXPECTED_HEADER


class LegacyCustomerDryRunTests(unittest.TestCase):
    def test_report_is_aggregate_only_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cust.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=EXPECTED_HEADER)
                writer.writeheader()
                writer.writerow({"c_no": "0001", "c_name": "Synthetic One", "c_tax": "1", "bpoint": "0"})
                writer.writerow({"c_no": " 0001 ", "c_name": "Synthetic Two", "c_tax": "", "bpoint": "9"})
            first = MODULE.build_customer_report(source)
            self.assertEqual(first, MODULE.build_customer_report(source))
            self.assertEqual(first["counts"]["data_rows"], 2)
            self.assertEqual(first["counts"]["duplicate_code_extra_rows"], 1)
            self.assertFalse(first["apply_performed"])
            serialized = str(first)
            self.assertNotIn("Synthetic One", serialized)
            self.assertNotIn("Synthetic Two", serialized)
            output = Path(directory) / "report.json"
            MODULE.write_report(first, output)
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
