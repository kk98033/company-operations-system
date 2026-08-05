"""Safe construction of integration settings from the local dotenv file."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values

from app.core.config import AppSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEST_PASSWORD = "company-system-test-only"


def load_database_test_settings() -> AppSettings:
    """Build a guarded test DSN without printing or exporting its password."""

    values = dotenv_values(PROJECT_ROOT / ".env")
    password = os.getenv("POSTGRES_TEST_PASSWORD") or values.get(
        "POSTGRES_TEST_PASSWORD"
    )
    password = password or DEFAULT_TEST_PASSWORD

    database_name = (
        os.getenv("POSTGRES_TEST_DB")
        or values.get("POSTGRES_TEST_DB")
        or "company_system_test"
    )
    username = (
        os.getenv("POSTGRES_TEST_USER")
        or values.get("POSTGRES_TEST_USER")
        or "company_system_test"
    )
    port = (
        os.getenv("POSTGRES_TEST_PORT")
        or values.get("POSTGRES_TEST_PORT")
        or "5433"
    )
    database_url = (
        f"postgresql+psycopg://{quote(username, safe='')}:{quote(password, safe='')}"
        f"@127.0.0.1:{port}/{quote(database_name, safe='')}"
    )
    return AppSettings.model_validate(
        {
            "APP_ENV": "test",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "8000",
            "DATABASE_URL": database_url,
        }
    )
