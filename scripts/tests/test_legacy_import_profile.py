from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "legacy_import_profile.py"


class LegacyImportProfileTests(unittest.TestCase):
    def run_profile(self, source_dir: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--source-dir",
                str(source_dir),
                "--output-dir",
                str(output_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_profiles_counts_without_exporting_row_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            (source_dir / "cust.csv").write_text(
                'id,name\nA1,測試\x01客戶\nA2,"含,逗號"\nA2,重複\n,空白鍵\n',
                encoding="utf-8",
            )

            result = self.run_profile(source_dir, output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            report_text = (output_dir / "legacy_source_profile.json").read_text(encoding="utf-8")
            report = json.loads(report_text)
            table = report["tables"][0]
            self.assertEqual(table["data_rows"], 4)
            self.assertEqual(table["unique_first_key_count"], 2)
            self.assertEqual(table["duplicate_first_key_extra_count"], 1)
            self.assertEqual(table["empty_first_key_count"], 1)
            self.assertEqual(table["control_character_codepoints"], {"U+0001": 1})
            self.assertNotIn("測試客戶", report_text)
            self.assertNotIn("含,逗號", report_text)

    def test_report_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source_dir = root / "source"
            first_output = root / "first"
            second_output = root / "second"
            source_dir.mkdir()
            (source_dir / "sample.csv").write_text("id,value\n1,a\n", encoding="utf-8")

            first = self.run_profile(source_dir, first_output)
            second = self.run_profile(source_dir, second_output)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                (first_output / "legacy_source_profile.json").read_bytes(),
                (second_output / "legacy_source_profile.json").read_bytes(),
            )

    def test_marks_invalid_utf8_without_exposing_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            (source_dir / "invalid.csv").write_bytes(b"id,name\n1,\xff\n")

            result = self.run_profile(source_dir, output_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output_dir / "legacy_source_profile.json").read_text(encoding="utf-8"))
            self.assertFalse(report["tables"][0]["valid_utf8"])
            self.assertEqual(report["summary"]["invalid_utf8_files"], 1)

    def test_refuses_to_write_inside_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            source_dir = Path(temporary_dir) / "source"
            source_dir.mkdir()
            (source_dir / "sample.csv").write_text("id,value\n1,a\n", encoding="utf-8")

            result = self.run_profile(source_dir, source_dir / "report")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the read-only source directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
