"""Migration behavior for one-to-one company settings defaults."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from app.core.database import create_database_resources
from app.modules.organizations.models import Organization, OrganizationSettings
from tests.integration.database_settings import load_database_test_settings

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_organization_settings_migration_backfills_existing_company(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = load_database_test_settings()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", settings.host)
    monkeypatch.setenv("APP_PORT", str(settings.port))
    monkeypatch.setenv("DATABASE_URL", settings.database_url_value())
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    organization_id = uuid4()

    command.downgrade(config, "0008_organization_profile")
    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            connection.execute(
                Organization.__table__.insert(),
                {"id": organization_id, "name": "Synthetic Existing Organization"},
            )
    finally:
        resources.dispose()

    command.upgrade(config, "head")
    resources = create_database_resources(settings)
    try:
        with resources.engine.begin() as connection:
            row = connection.execute(
                OrganizationSettings.__table__.select().where(
                    OrganizationSettings.organization_id == organization_id
                )
            ).one()
            assert row.statement_tax_default_enabled is False
            assert row.document_number_policy_version == "adr-018-v1"
            connection.execute(
                OrganizationSettings.__table__.delete().where(
                    OrganizationSettings.organization_id == organization_id
                )
            )
            connection.execute(
                Organization.__table__.delete().where(Organization.id == organization_id)
            )
    finally:
        resources.dispose()
