from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import (
    AppEnvironment,
    AppSettings,
    SettingsLoadError,
    load_settings,
)
from tests.settings_factory import valid_settings_values


def test_missing_required_variables_are_reported_together() -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(environ={}, env_file=None)

    assert str(error.value) == (
        "缺少必要環境變數: APP_ENV, APP_HOST, APP_PORT, DATABASE_URL, "
        "APP_PUBLIC_ORIGIN, CSRF_HMAC_KEY, AUTH_SECURITY_HMAC_KEY"
    )


def test_process_environment_overrides_dotenv_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                "APP_HOST=127.0.0.1",
                "APP_PORT=9000",
                (
                    "DATABASE_URL=postgresql+psycopg://company_system_dev:"
                    "secret@127.0.0.1/company_system_dev"
                ),
                "APP_PUBLIC_ORIGIN=http://127.0.0.1:5173",
                "CSRF_HMAC_KEY=dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE",
                "AUTH_SECURITY_HMAC_KEY=dGVzdC1vbmx5LWF1dGgta2V5LTMyLWJ5dGVzISEhISE",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(
        environ={
            "APP_ENV": "test",
            "DATABASE_URL": (
                "postgresql+psycopg://company_system_test:secret@127.0.0.1/"
                "company_system_test"
            ),
        },
        env_file=env_file,
    )

    assert settings.environment is AppEnvironment.TEST
    assert settings.port == 9000
    assert settings.database_url_value().endswith("/company_system_test")


def test_dotenv_expands_postgres_components_into_database_url(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=development",
                "APP_HOST=127.0.0.1",
                "APP_PORT=8000",
                "POSTGRES_DB=company_system_dev",
                "POSTGRES_USER=company_system_dev",
                "POSTGRES_PASSWORD=local-only",
                "POSTGRES_HOST=127.0.0.1",
                "POSTGRES_PORT=5432",
                (
                    "DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:"
                    "${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/"
                    "${POSTGRES_DB}"
                ),
                "APP_PUBLIC_ORIGIN=http://127.0.0.1:5173",
                "CSRF_HMAC_KEY=dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE",
                "AUTH_SECURITY_HMAC_KEY=dGVzdC1vbmx5LWF1dGgta2V5LTMyLWJ5dGVzISEhISE",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(environ={}, env_file=env_file)

    assert settings.database_url_value() == (
        "postgresql+psycopg://company_system_dev:local-only@127.0.0.1:5432/"
        "company_system_dev"
    )


def test_settings_and_validation_error_repr_hide_database_secret() -> None:
    settings = AppSettings.model_validate(valid_settings_values())

    assert "local-only" not in repr(settings)

    invalid_values = valid_settings_values(
        DATABASE_URL=["validation-canary"]
    )
    with pytest.raises(ValidationError) as error:
        AppSettings.model_validate(invalid_values)

    assert "validation-canary" not in str(error.value)
    assert "validation-canary" not in repr(error.value)


def test_validation_error_hides_all_input_values() -> None:
    values = valid_settings_values(
        APP_PORT="invalid-port-canary",
        DATABASE_URL=12345,
    )

    with pytest.raises(SettingsLoadError) as error:
        load_settings(environ=values, env_file=None)

    message = str(error.value)
    assert "APP_PORT" in message
    assert "DATABASE_URL" in message
    assert "invalid-port-canary" not in message
    assert "12345" not in message


def test_invalid_environment_has_clear_variable_name() -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(APP_ENV="staging"),
            env_file=None,
        )

    assert "APP_ENV" in str(error.value)
    assert "staging" not in str(error.value)


@pytest.mark.parametrize(
    "origin",
    [
        "https://company.example/path",
        "https://user@company.example",
        "https://company.example?query=1",
        "https://*.company.example",
        "https://company.example:notaport",
    ],
)
def test_public_origin_rejects_non_origin_values(origin: str) -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(APP_PUBLIC_ORIGIN=origin),
            env_file=None,
        )

    assert "APP_PUBLIC_ORIGIN" in str(error.value)
    assert origin not in str(error.value)


def test_production_requires_https_public_origin() -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(
                APP_ENV="production",
                APP_PUBLIC_ORIGIN="http://company.example",
                DATABASE_URL=(
                    "postgresql+psycopg://company_system_prod:production-only"
                    "@database.internal/company_system_prod"
                ),
            ),
            env_file=None,
        )

    assert "APP_PUBLIC_ORIGIN" in str(error.value)


@pytest.mark.parametrize(
    "csrf_key",
    ["short", "replace-with-token-urlsafe-32-byte-value", "!" * 43],
)
def test_csrf_key_rejects_weak_or_placeholder_values_without_echo(
    csrf_key: str,
) -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(CSRF_HMAC_KEY=csrf_key),
            env_file=None,
        )

    assert "CSRF_HMAC_KEY" in str(error.value)
    assert csrf_key not in str(error.value)


@pytest.mark.parametrize(
    "security_key",
    [
        "short",
        "replace-with-a-different-token-urlsafe-32-byte-value",
        "!" * 43,
        "dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE",
    ],
)
def test_auth_security_key_rejects_weak_values_without_echo(
    security_key: str,
) -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(AUTH_SECURITY_HMAC_KEY=security_key),
            env_file=None,
        )

    assert "AUTH_SECURITY_HMAC_KEY" in str(error.value)
    assert security_key not in str(error.value)
