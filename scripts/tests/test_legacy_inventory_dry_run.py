import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "legacy_inventory_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_inventory_dry_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryDryRunTest(unittest.TestCase):
    def test_reports_balance_relationships_without_exposing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            with (source / "subpoena.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["id"])
                writer.writeheader()
                writer.writerows([{"id": "WO-A"}, {"id": "WO-B"}, {"id": "WO-C"}])
            merchandise = (
                "auto_id,subpoenaid,finishnumber,delivernumber,sparenumber,customername\n"
                "1,WO-A,100,60,10,private-a\n"
                "2,WO-B,10,10,0,private-b\n"
                "3,WO-D,5,7,0,private-c\n"
                "4,\x00WO-A,invalid,0,0,private-d\n"
            )
            (source / "merchandise.csv").write_bytes(merchandise.encode())

            report = MODULE.build_report(source)

            self.assertEqual(report["counts"]["inventory_rows"], 4)
            self.assertEqual(report["counts"]["matched_work_order_rows"], 3)
            self.assertEqual(report["counts"]["orphan_work_order_rows"], 1)
            self.assertEqual(report["counts"]["invalid_quantity_rows"], 1)
            self.assertEqual(report["counts"]["negative_balance_rows"], 1)
            self.assertEqual(report["source"]["nul_bytes_sanitized"], 1)
            self.assertFalse(report["apply_performed"])
            self.assertNotIn("private", str(report))


if __name__ == "__main__":
    unittest.main()
