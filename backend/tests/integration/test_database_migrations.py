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
from app.modules.imports.models import ImportRun
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

IDENTITY_TABLES = [
    "organization_members",
    "organizations",
    "sessions",
    "users",
]


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
    assert _current_revision() == "0004_identity_foundation"
    assert _table_names() == ["alembic_version", *IMPORT_TABLES, *IDENTITY_TABLES]

    command.check(config)

    command.downgrade(config, "base")
    assert _current_revision() is None
    assert _table_names() == ["alembic_version"]

    command.upgrade(config, "head")
    assert _current_revision() == "0004_identity_foundation"
    assert _table_names() == ["alembic_version", *IMPORT_TABLES, *IDENTITY_TABLES]


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
            assert connection.scalar(
                ImportRun.__table__.select()
                .with_only_columns(ImportRun.id)
                .where(ImportRun.id == run_id)
            ) == run_id
    finally:
        resources.dispose()

    command.upgrade(config, "head")
    assert _current_revision() == "0004_identity_foundation"
    command.check(config)

    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            assert connection.scalar(
                ImportRun.__table__.select()
                .with_only_columns(ImportRun.id)
                .where(ImportRun.id == run_id)
            ) == run_id
            connection.execute(
                ImportRun.__table__.delete().where(ImportRun.id == run_id)
            )
    finally:
        resources.dispose()
