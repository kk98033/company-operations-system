"""Spreadsheet-safe CSV primitives."""

from app.modules.operations.csv_export import render_csv, safe_csv_cell


def test_formula_like_cells_are_neutralized_without_changing_normal_text() -> None:
    assert safe_csv_cell("一般客戶") == "一般客戶"
    assert safe_csv_cell("=1+1") == "'=1+1"
    assert safe_csv_cell("  @SUM(A1:A2)") == "'  @SUM(A1:A2)"
    assert safe_csv_cell("-10") == "'-10"


def test_csv_is_utf8_bom_and_uses_crlf() -> None:
    content = render_csv(["名稱"], [["測試"]])
    assert content.startswith(b"\xef\xbb\xbf")
    assert content.decode("utf-8-sig") == "名稱\r\n測試\r\n"
