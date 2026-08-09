"""Shared fixtures for isolated PostgreSQL integration tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from app.core.database import create_database_resources
from app.modules.auth.models import Session, User
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from app.modules.organizations.models import Organization, OrganizationMember
from tests.integration.database_settings import load_database_test_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def migrated_engine(monkeypatch: pytest.MonkeyPatch) -> Generator[Engine, None, None]:
    """Provide an engine after upgrading the isolated test database to head."""

    settings = load_database_test_settings()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_HOST", settings.host)
    monkeypatch.setenv("APP_PORT", str(settings.port))
    monkeypatch.setenv("DATABASE_URL", settings.database_url_value())
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")

    resources = create_database_resources(settings)
    try:
        yield resources.engine
    finally:
        resources.dispose()


@pytest.fixture
def identity_engine(migrated_engine: Engine) -> Generator[Engine, None, None]:
    """Keep committed identity fixtures isolated from every neighboring test."""

    try:
        yield migrated_engine
    finally:
        with migrated_engine.begin() as connection:
            connection.execute(Session.__table__.delete())
            connection.execute(OrganizationMemberRole.__table__.delete())
            connection.execute(RolePermission.__table__.delete())
            connection.execute(Role.__table__.delete())
            connection.execute(Permission.__table__.delete())
            connection.execute(OrganizationMember.__table__.delete())
            connection.execute(User.__table__.delete())
            connection.execute(Organization.__table__.delete())
