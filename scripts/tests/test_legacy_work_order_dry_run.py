import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "legacy_work_order_dry_run.py"
SPEC = importlib.util.spec_from_file_location("legacy_work_order_dry_run", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkOrderDryRunTest(unittest.TestCase):
    def test_reports_relationships_without_exposing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            with (source / "subpoena.csv").open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "id",
                        "idbuffer",
                        "customername",
                        "ordername",
                        "ordernumber",
                        "deliverydate",
                        "unitprice",
                        "remark",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"id": "WO-A", "customername": "private-a"},
                        {"id": "WO-A", "customername": "private-b"},
                        {"id": "WO-B", "ordername": "private-product"},
                    ]
                )
            with (source / "quote.csv").open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "auto_id",
                        "subpoenaid",
                        "oplatefactory",
                        "bplatefactory",
                        "oprintfactory",
                        "bprintfactory",
                        "odeliverfactory",
                        "bdeliverfactory",
                        "oremark",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"auto_id": "1", "subpoenaid": "WO-A"},
                        {"auto_id": "2", "subpoenaid": "MISSING"},
                    ]
                )
            report = MODULE.build_report(source)
            self.assertEqual(report["counts"]["work_order_rows"], 3)
            self.assertEqual(report["counts"]["duplicate_work_order_id_extra_rows"], 1)
            self.assertEqual(report["counts"]["orphan_process_rows"], 1)
            self.assertFalse(report["apply_performed"])
            self.assertNotIn("private", str(report))


if __name__ == "__main__":
    unittest.main()
