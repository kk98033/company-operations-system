import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "legacy_billing_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_billing_dry_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BillingDryRunTest(unittest.TestCase):
    def test_aggregate_reconciliation_never_exposes_customer_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            fixtures = {
                "rec.csv": (
                    [
                        "idno",
                        "yrmn",
                        "pcount",
                        "count1",
                        "rcut",
                        "rec",
                        "unrec",
                        "rec_da",
                        "used",
                    ],
                    [["PRIVATE", "202601", "0", "100", "0", "20", "80", "", ""]],
                ),
                "income.csv": (
                    [
                        "income_da",
                        "sno",
                        "c_no",
                        "yrmn",
                        "rcut",
                        "count1",
                        "count2",
                        "bank",
                        "acc_no",
                        "p_da",
                        "w_m",
                        "unrec",
                    ],
                    [
                        [
                            "20260102",
                            "1",
                            "PRIVATE",
                            "202601",
                            "0",
                            "20",
                            "0",
                            "SECRET-BANK",
                            "",
                            "",
                            "",
                            "80",
                        ]
                    ],
                ),
                "lsm.csv": (
                    ["yrmn", "c_no", "total", "tax", "suma"],
                    [["202601", "PRIVATE", "100", "5", "105"]],
                ),
                "rece.csv": (
                    ["c_no", "yrmn", "rec_tot", "ptotal", "pay"],
                    [["PRIVATE", "202601", "20", "100", "0"]],
                ),
            }
            for filename, (fields, rows) in fixtures.items():
                with (source / filename).open(
                    "w", encoding="utf-8", newline=""
                ) as handle:
                    writer = csv.writer(handle)
                    writer.writerow(fields)
                    writer.writerows(rows)
            report = MODULE.build_report(source)
            self.assertEqual(
                report["counts"]["relations"]["income_keys_matching_rec"], 1
            )
            self.assertEqual(report["counts"]["lsm"]["amount_totals"]["tax"], "5")
            self.assertFalse(report["apply_performed"])
            self.assertNotIn("PRIVATE", str(report))
            self.assertNotIn("SECRET-BANK", str(report))


if __name__ == "__main__":
    unittest.main()
