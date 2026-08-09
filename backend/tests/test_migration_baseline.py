"""Static guardrails for the baseline and first infrastructure migration."""

import importlib.util
from pathlib import Path
from types import ModuleType

from app.core.database import Base
from app.core.database.model_registry import REGISTERED_MODELS

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = BACKEND_ROOT / "migrations/versions/0001_empty_baseline.py"


def _load_baseline() -> ModuleType:
    spec = importlib.util.spec_from_file_location("empty_baseline", BASELINE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_base_metadata_contains_import_and_identity_foundation_tables() -> None:
    assert REGISTERED_MODELS
    assert set(Base.metadata.tables) == {
        "import_errors",
        "import_runs",
        "import_source_files",
        "import_staging_records",
        "legacy_mappings",
        "organization_members",
        "organizations",
        "sessions",
        "users",
    }
    assert "customers" not in Base.metadata.tables


def test_empty_baseline_upgrade_and_downgrade_are_safe_no_ops() -> None:
    baseline = _load_baseline()

    assert baseline.revision == "0001_empty_baseline"
    assert baseline.down_revision is None
    assert baseline.upgrade() is None
    assert baseline.downgrade() is None
