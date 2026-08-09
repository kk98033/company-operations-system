"""End-to-end CLI check against the isolated PostgreSQL service."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from secrets import token_urlsafe

import pytest
from sqlalchemy import Engine

from tests.integration.database_settings import load_database_test_settings

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_cli_seeds_and_reruns_without_printing_secrets(
    identity_engine: Engine,
) -> None:
    settings = load_database_test_settings()
    admin_password = token_urlsafe(24)
    operator_password = token_urlsafe(24)
    environment = {
        **os.environ,
        "APP_ENV": "test",
        "APP_HOST": settings.host,
        "APP_PORT": str(settings.port),
        "DATABASE_URL": settings.database_url_value(),
        "TEST_ADMIN_SEED_PASSWORD": admin_password,
        "TEST_OPERATOR_SEED_PASSWORD": operator_password,
    }

    first_run = subprocess.run(
        [sys.executable, "scripts/seed_test_identity.py"],
        cwd=BACKEND_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    second_run = subprocess.run(
        [sys.executable, "scripts/seed_test_identity.py"],
        cwd=BACKEND_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert first_run.returncode == 0
    assert "organizations +1, users +2, memberships +2" in first_run.stdout
    assert second_run.returncode == 0
    assert "organizations +0, users +0, memberships +0" in second_run.stdout
    combined_output = (
        first_run.stdout
        + first_run.stderr
        + second_run.stdout
        + second_run.stderr
    )
    assert admin_password not in combined_output
    assert operator_password not in combined_output
    assert "$argon2" not in combined_output
    assert "postgresql" not in combined_output
