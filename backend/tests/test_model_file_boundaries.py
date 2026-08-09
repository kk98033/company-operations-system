"""Maintainability gates for model, migration, and test Python files."""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_model_migration_and_test_files_stay_below_python_size_gate() -> None:
    production_files = [
        *sorted((BACKEND_ROOT / "app/modules").glob("*/models/*.py")),
        *sorted((BACKEND_ROOT / "migrations/versions").glob("*.py")),
        *sorted((BACKEND_ROOT / "tests").glob("**/*.py")),
    ]

    assert production_files
    assert all(len(path.read_text().splitlines()) <= 300 for path in production_files)
