"""PostgreSQL integration checks for readiness and session lifecycle."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.database import DatabaseReadinessCheck, create_database_resources
from tests.integration.database_settings import load_database_test_settings

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def test_isolated_postgres_accepts_readiness_and_session_query() -> None:
    resources = create_database_resources(load_database_test_settings())
    try:
        assert DatabaseReadinessCheck(resources.engine)().status == "ok"
        with resources.session_factory() as session:
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        resources.dispose()


def test_separate_sessions_do_not_share_uncommitted_state() -> None:
    resources = create_database_resources(load_database_test_settings())
    try:
        with resources.session_factory() as first_session:
            first_session.execute(text("CREATE TEMP TABLE slice05_dirty(value int)"))
            first_session.execute(text("INSERT INTO slice05_dirty VALUES (1)"))

        with resources.session_factory() as second_session:
            relation = second_session.scalar(
                text("SELECT to_regclass('pg_temp.slice05_dirty')")
            )
            assert relation is None
    finally:
        resources.dispose()
