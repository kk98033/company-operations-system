"""Unit tests for safe isolated PostgreSQL integration configuration."""

from urllib.parse import urlsplit

import pytest

from tests.integration.database_settings import load_database_test_settings


def test_database_test_settings_encode_reserved_dsn_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_TEST_USER", "company_system_test-user@example")
    monkeypatch.setenv("POSTGRES_TEST_PASSWORD", "p@ss:/word?#")
    monkeypatch.setenv("POSTGRES_TEST_DB", "company_system_test-special")

    settings = load_database_test_settings()
    database_url = settings.database_url_value()
    parsed = urlsplit(database_url)

    assert parsed.username == "company_system_test-user%40example"
    assert parsed.password == "p%40ss%3A%2Fword%3F%23"
    assert "%40" in database_url
    assert "p@ss:/word?#" not in database_url
