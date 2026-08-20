"""Alembic round-trip verification on isolated PostgreSQL."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.core.database import create_database_resources
from app.core.database.model_registry import REGISTERED_MODELS
from app.modules.auth.models import User
from app.modules.imports.models import ImportRun
from app.modules.master_data.models import ProcessDefinition
from app.modules.organizations.models import Organization, OrganizationMember, OrganizationSettings
from tests.integration.database_settings import load_database_test_settings

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def _current_revision() -> str | None:
    resources = create_database_resources(load_database_test_settings())
    try:
        with resources.engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        resources.dispose()


def _table_names() -> list[str]:
    resources = create_database_resources(load_database_test_settings())
    try:
        return sorted(inspect(resources.engine).get_table_names())
    finally:
        resources.dispose()


IMPORT_TABLES = [
    "import_errors",
    "import_runs",
    "import_source_files",
    "import_staging_records",
    "legacy_mappings",
]
IDENTITY_TABLES = ["organization_members", "organizations", "sessions", "users"]
ORGANIZATION_SETTINGS_TABLES = ["organization_settings"]
CUSTOMER_TABLES = ["customers"]
CUSTOMER_WORK_ITEM_TABLES = ["customer_work_items"]
QUOTATION_TABLES = ["document_sequences", "quotation_items", "quotations"]
WORK_ORDER_TABLES = ["production_cases", "work_order_attachments", "work_orders"]
PRODUCTION_TABLES = [
    "final_completion_entries",
    "inventory_adjustments",
    "inventory_ledger",
    "process_events",
]
SHIPMENT_TABLES = ["shipment_items", "shipments"]
PRICING_TABLES = ["price_history", "pricing_documents", "pricing_items"]
BILLING_TABLES = ["receipt_allocations", "receipts", "statement_items", "statements"]
MASTER_DATA_TABLES = ["paper_mills", "paper_types", "process_definitions", "vendors"]
AUTHORIZATION_TABLES = [
    "organization_member_roles",
    "permissions",
    "role_permissions",
    "roles",
]
AUDIT_TABLES = ["audit_logs"]
LOGIN_SECURITY_TABLES = ["login_security_events", "login_throttle_states"]


def test_schema_upgrade_downgrade_upgrade_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_database_test_settings()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", settings.host)
    monkeypatch.setenv("APP_PORT", str(settings.port))
    monkeypatch.setenv("DATABASE_URL", settings.database_url_value())
    config = _alembic_config()
    assert REGISTERED_MODELS

    command.upgrade(config, "head")
    assert _current_revision() == "0027_security_events"
    assert _table_names() == [
        "alembic_version",
        *sorted(
            [
                *IMPORT_TABLES,
                *AUTHORIZATION_TABLES,
                *AUDIT_TABLES,
                *LOGIN_SECURITY_TABLES,
                *IDENTITY_TABLES,
                *ORGANIZATION_SETTINGS_TABLES,
                *CUSTOMER_TABLES,
                *CUSTOMER_WORK_ITEM_TABLES,
                *QUOTATION_TABLES,
                *WORK_ORDER_TABLES,
                *PRODUCTION_TABLES,
                *SHIPMENT_TABLES,
                *PRICING_TABLES,
                *BILLING_TABLES,
                "document_exports",
                *MASTER_DATA_TABLES,
            ]
        ),
    ]

    command.check(config)
    command.downgrade(config, "base")
    assert _current_revision() is None
    assert _table_names() == ["alembic_version"]

    command.upgrade(config, "head")
    assert _current_revision() == "0027_security_events"
    assert _table_names() == [
        "alembic_version",
        *sorted(
            [
                *IMPORT_TABLES,
                *AUTHORIZATION_TABLES,
                *AUDIT_TABLES,
                *LOGIN_SECURITY_TABLES,
                *IDENTITY_TABLES,
                *ORGANIZATION_SETTINGS_TABLES,
                *CUSTOMER_TABLES,
                *CUSTOMER_WORK_ITEM_TABLES,
                *QUOTATION_TABLES,
                *WORK_ORDER_TABLES,
                *PRODUCTION_TABLES,
                *SHIPMENT_TABLES,
                *PRICING_TABLES,
                *BILLING_TABLES,
                "document_exports",
                *MASTER_DATA_TABLES,
            ]
        ),
    ]


def test_identity_downgrade_preserves_existing_import_foundation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_database_test_settings()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", settings.host)
    monkeypatch.setenv("APP_PORT", str(settings.port))
    monkeypatch.setenv("DATABASE_URL", settings.database_url_value())
    config = _alembic_config()
    run_id = uuid4()

    command.upgrade(config, "head")
    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            connection.execute(
                ImportRun.__table__.insert(),
                {
                    "id": run_id,
                    "source_system": "synthetic_identity_roundtrip",
                    "source_manifest_sha256": "9" * 64,
                    "importer_version": "test-only-v1",
                },
            )
    finally:
        resources.dispose()

    command.downgrade(config, "0003_import_trace")
    assert _current_revision() == "0003_import_trace"
    assert _table_names() == ["alembic_version", *IMPORT_TABLES]

    resources = create_database_resources(settings)
    try:
        with resources.engine.connect() as connection:
            assert (
                connection.scalar(
                    ImportRun.__table__.select()
                    .with_only_columns(ImportRun.id)
                    .where(ImportRun.id == run_id)
                )
                == run_id
            )
    finally:
        resources.dispose()
    command.upgrade(config, "head")
    assert _current_revision() == "0027_security_events"
    command.check(config)
    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            assert (
                connection.scalar(
                    ImportRun.__table__.select()
                    .with_only_columns(ImportRun.id)
                    .where(ImportRun.id == run_id)
                )
                == run_id
            )
            connection.execute(ImportRun.__table__.delete().where(ImportRun.id == run_id))
    finally:
        resources.dispose()


def test_authorization_downgrade_preserves_existing_identity_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_database_test_settings()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", settings.host)
    monkeypatch.setenv("APP_PORT", str(settings.port))
    monkeypatch.setenv("DATABASE_URL", settings.database_url_value())
    config = _alembic_config()
    organization_id, user_id, member_id = uuid4(), uuid4(), uuid4()

    command.upgrade(config, "head")
    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            connection.execute(
                Organization.__table__.insert(),
                {"id": organization_id, "name": "Synthetic Migration Organization"},
            )
            connection.execute(
                User.__table__.insert(),
                {
                    "id": user_id,
                    "login_name": f"synthetic.migration.{user_id.hex}",
                    "display_name": "Synthetic Migration User",
                    "password_hash": "$argon2id$synthetic-migration-only",
                },
            )
            connection.execute(
                OrganizationMember.__table__.insert(),
                {
                    "id": member_id,
                    "organization_id": organization_id,
                    "user_id": user_id,
                },
            )
    finally:
        resources.dispose()

    command.downgrade(config, "0004_identity_foundation")
    assert _current_revision() == "0004_identity_foundation"
    assert _table_names() == ["alembic_version", *IMPORT_TABLES, *IDENTITY_TABLES]

    resources = create_database_resources(settings)
    try:
        with resources.engine.connect() as connection:
            assert (
                connection.scalar(
                    OrganizationMember.__table__.select()
                    .with_only_columns(OrganizationMember.id)
                    .where(OrganizationMember.id == member_id)
                )
                == member_id
            )
    finally:
        resources.dispose()

    command.upgrade(config, "head")
    command.check(config)
    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            connection.execute(
                OrganizationMember.__table__.delete().where(OrganizationMember.id == member_id)
            )
            connection.execute(User.__table__.delete().where(User.id == user_id))
            connection.execute(
                OrganizationSettings.__table__.delete().where(
                    OrganizationSettings.organization_id == organization_id
                )
            )
            connection.execute(
                ProcessDefinition.__table__.delete().where(
                    ProcessDefinition.organization_id == organization_id
                )
            )
            connection.execute(
                Organization.__table__.delete().where(Organization.id == organization_id)
            )
    finally:
        resources.dispose()
