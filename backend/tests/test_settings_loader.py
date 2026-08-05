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
        "缺少必要環境變數: APP_ENV, APP_HOST, APP_PORT, DATABASE_URL"
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
