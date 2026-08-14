"""Fixed-schema CSV exports safe for spreadsheet applications."""

import csv
import io
from collections.abc import Iterable


def safe_csv_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + text
    return text


def render_csv(headers: list[str], rows: Iterable[Iterable[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([safe_csv_cell(value) for value in row])
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")
