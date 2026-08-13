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
        "audit_logs",
        "customers",
        "customer_work_items",
        "document_sequences",
        "quotation_items",
        "quotations",
        "production_cases",
        "work_orders",
        "work_order_attachments",
        "process_events",
        "final_completion_entries",
        "inventory_adjustments",
        "inventory_ledger",
        "shipments",
        "shipment_items",
        "pricing_documents",
        "pricing_items",
        "price_history",
        "statements",
        "statement_items",
        "receipts",
        "receipt_allocations",
        "document_exports",
        "paper_mills",
        "paper_types",
        "process_definitions",
        "vendors",
        "import_errors",
        "import_runs",
        "import_source_files",
        "import_staging_records",
        "legacy_mappings",
        "login_security_events",
        "login_throttle_states",
        "organization_member_roles",
        "organization_members",
        "organization_settings",
        "organizations",
        "permissions",
        "role_permissions",
        "roles",
        "sessions",
        "users",
    }


def test_empty_baseline_upgrade_and_downgrade_are_safe_no_ops() -> None:
    baseline = _load_baseline()

    assert baseline.revision == "0001_empty_baseline"
    assert baseline.down_revision is None
    assert baseline.upgrade() is None
    assert baseline.downgrade() is None
