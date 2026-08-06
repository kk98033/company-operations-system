"""Export the application OpenAPI document without starting an HTTP server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def serialize_openapi() -> str:
    """Return stable UTF-8 JSON text for drift checks and client generation."""

    document = json.dumps(
        app.openapi(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{document}\n"


def main() -> None:
    output_path = parse_args().output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_openapi(), encoding="utf-8")


if __name__ == "__main__":
    main()
