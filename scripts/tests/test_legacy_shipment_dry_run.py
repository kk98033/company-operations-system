import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "legacy_shipment_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_shipment_dry_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class ShipmentDryRunTest(unittest.TestCase):
    def test_reports_relations_without_exposing_business_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            fixtures = {
                "subp_sale.csv": (["saledate", "deliverid", "customername", "deliverrows", "remark"], [["20260101", "S1", "private-customer", "1", "private-note"], ["20260102", "S2", "private", "0", "private"]]),
                "subp_sale2.csv": (["deliverid", "deliversn", "delivernumber", "sparenumber", "subpoenaid", "tr_ok"], [["S1", "1", "10", "2", "WO1", "1"], ["BAD", "1", "1", "0", "WOX", "0"]]),
                "subpoena.csv": (["id"], [["WO1"]]),
            }
            for filename, (fields, rows) in fixtures.items():
                with (source / filename).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle); writer.writerow(fields); writer.writerows(rows)
            report = MODULE.build_report(source)
            self.assertEqual(report["counts"]["shipment_headers"], 2)
            self.assertEqual(report["counts"]["shipment_items"], 2)
            self.assertEqual(report["counts"]["headers_without_items"], 1)
            self.assertEqual(report["counts"]["orphan_header_items"], 1)
            self.assertEqual(report["counts"]["matched_work_order_items"], 1)
            self.assertEqual(report["counts"]["spare_quantity_total"], "2")
            self.assertFalse(report["apply_performed"])
            self.assertNotIn("private", str(report))


if __name__ == "__main__": unittest.main()
