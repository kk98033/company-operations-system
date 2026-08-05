from __future__ import annotations

import pytest

from app.core.config import AppEnvironment, SettingsLoadError, load_settings
from tests.settings_factory import database_url_for, valid_settings_values


@pytest.mark.parametrize(
    "unsafe_database_name",
    ["company_system_dev", "company_system", "company_system_production"],
)
def test_test_environment_rejects_non_test_database(
    unsafe_database_name: str,
) -> None:
    database_url = (
        "postgresql+psycopg://company_system_test:do-not-leak"
        f"@database.internal/{unsafe_database_name}"
    )

    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(
                APP_ENV="test",
                DATABASE_URL=database_url,
            ),
            env_file=None,
        )

    assert "test 環境" in str(error.value)
    assert "必須含有對應的獨立標記" in str(error.value)
    assert "do-not-leak" not in str(error.value)
    assert unsafe_database_name not in str(error.value)


@pytest.mark.parametrize(
    "test_database_name",
    ["company_system_test", "test_company_system", "company-test-ci"],
)
def test_test_environment_accepts_explicit_test_database(
    test_database_name: str,
) -> None:
    settings = load_settings(
        environ=valid_settings_values(
            APP_ENV="test",
            DATABASE_URL=(
                "postgresql+psycopg://company_system_test:test-only"
                f"@database.internal/{test_database_name}"
            ),
        ),
        env_file=None,
    )

    assert settings.environment is AppEnvironment.TEST


def test_production_environment_accepts_isolated_database_and_username() -> None:
    settings = load_settings(
        environ=valid_settings_values(
            APP_ENV="production",
            DATABASE_URL=database_url_for(
                "production",
                "company_system_prod",
            ),
        ),
        env_file=None,
    )

    assert settings.environment is AppEnvironment.PRODUCTION


def test_invalid_database_scheme_does_not_echo_database_url() -> None:
    database_url = "sqlite:///tmp/company_system_dev?password=do-not-leak"

    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(DATABASE_URL=database_url),
            env_file=None,
        )

    assert "必須使用 PostgreSQL" in str(error.value)
    assert "do-not-leak" not in str(error.value)
    assert database_url not in str(error.value)


@pytest.mark.parametrize(
    "placeholder",
    [
        "replace-with-local-only-password",
        "replace-with-test-only-password",
    ],
)
def test_example_database_password_is_rejected(placeholder: str) -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(
                DATABASE_URL=(
                    "postgresql+psycopg://company_system_dev:"
                    f"{placeholder}@127.0.0.1/"
                    "company_system_dev"
                )
            ),
            env_file=None,
        )

    assert "仍使用範例密碼" in str(error.value)
    assert placeholder not in str(error.value)


@pytest.mark.parametrize(
    ("environment", "database_name"),
    [
        ("development", "company_system_test"),
        ("development", "company_system_prod"),
        ("test", "company_system_dev"),
        ("test", "company_system_prod"),
        ("production", "company_system_dev"),
        ("production", "company_system_test"),
    ],
)
def test_each_environment_rejects_cross_environment_database(
    environment: str,
    database_name: str,
) -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(
                APP_ENV=environment,
                DATABASE_URL=database_url_for(
                    environment,
                    database_name,
                    password="canary-secret",
                ),
            ),
            env_file=None,
        )

    assert f"{environment} 環境" in str(error.value)
    assert "canary-secret" not in str(error.value)
    assert database_name not in str(error.value)


@pytest.mark.parametrize(
    ("environment", "mixed_database_name"),
    [
        ("development", "company_system_dev_test"),
        ("test", "company_system_dev_test"),
        ("production", "company_system_prod_test"),
    ],
)
def test_database_name_rejects_mixed_environment_markers(
    environment: str,
    mixed_database_name: str,
) -> None:
    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(
                APP_ENV=environment,
                DATABASE_URL=database_url_for(
                    environment,
                    mixed_database_name,
                ),
            ),
            env_file=None,
        )

    assert "資料庫名稱不得含有其他環境標記" in str(error.value)
    assert mixed_database_name not in str(error.value)


@pytest.mark.parametrize(
    ("environment", "database_username"),
    [
        ("development", "company_system_test"),
        ("test", "company_system_dev"),
        ("production", "company_system_prod_test"),
        ("production", "company_system"),
    ],
)
def test_database_username_must_match_only_current_environment(
    environment: str,
    database_username: str,
) -> None:
    marker = {
        "development": "dev",
        "test": "test",
        "production": "prod",
    }[environment]
    database_url = (
        f"postgresql+psycopg://{database_username}:canary-password"
        f"@database.internal/company_system_{marker}"
    )

    with pytest.raises(SettingsLoadError) as error:
        load_settings(
            environ=valid_settings_values(
                APP_ENV=environment,
                DATABASE_URL=database_url,
            ),
            env_file=None,
        )

    assert "資料庫帳號" in str(error.value)
    assert "canary-password" not in str(error.value)
    assert database_username not in str(error.value)


def test_database_url_requires_database_name_username_and_password() -> None:
    with pytest.raises(SettingsLoadError, match="必須指定資料庫名稱"):
        load_settings(
            environ=valid_settings_values(
                DATABASE_URL=(
                    "postgresql+psycopg://company_system_dev:secret@db"
                )
            ),
            env_file=None,
        )

    with pytest.raises(SettingsLoadError, match="必須指定資料庫帳號"):
        load_settings(
            environ=valid_settings_values(
                DATABASE_URL=(
                    "postgresql+psycopg://db.internal/company_system_dev"
                )
            ),
            env_file=None,
        )

    with pytest.raises(SettingsLoadError, match="必須指定資料庫密碼"):
        load_settings(
            environ=valid_settings_values(
                DATABASE_URL=(
                    "postgresql+psycopg://company_system_dev@db.internal/"
                    "company_system_dev"
                )
            ),
            env_file=None,
        )
