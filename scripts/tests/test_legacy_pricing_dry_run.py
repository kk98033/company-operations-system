import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "legacy_pricing_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_pricing_dry_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class PricingDryRunTest(unittest.TestCase):
    def test_reports_legacy_relations_and_amounts_without_business_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            fixtures = {
                "sal.csv": (["sal_da", "sno", "subpid", "c_no", "prodna", "amount", "pr_sum", "used", "s_memo", "orderid", "deliverid", "pna_s"], [["20260101", "1", "WO1", "private", "private-product", "10", "200", "", "private-note", "", "S1", ""]]),
                "sal2.csv": (["sal_da", "sno", "s_no", "contents", "amount", "sal_pr", "pr_tot"], [["20260101", "1", "1", "private-content", "10", "20", "200"], ["20260102", "2", "1", "private", "1", "5", "5"]]),
                "subp_sale.csv": (["deliverid"], [["S1"]]), "subpoena.csv": (["id"], [["WO1"]]),
            }
            for filename, (fields, rows) in fixtures.items():
                with (source / filename).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle); writer.writerow(fields); writer.writerows(rows)
            report = MODULE.build_report(source)
            self.assertEqual(report["counts"]["pricing_headers"], 1)
            self.assertEqual(report["counts"]["pricing_items"], 2)
            self.assertEqual(report["counts"]["orphan_header_items"], 1)
            self.assertEqual(report["counts"]["matched_shipment_headers"], 1)
            self.assertEqual(report["counts"]["matched_work_order_headers"], 1)
            self.assertEqual(report["counts"]["header_item_total_difference"], "-5")
            self.assertFalse(report["apply_performed"])
            self.assertNotIn("private", str(report))


if __name__ == "__main__": unittest.main()
