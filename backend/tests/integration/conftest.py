"""Shared fixtures for isolated PostgreSQL integration tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from app.core.database import create_database_resources
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
