"""Small test factory keeping valid configuration out of individual tests."""

from app.core.config import AppSettings


def valid_settings_values(**overrides: object) -> dict[str, object]:
    """Return mutable development settings for focused validation tests."""

    values: dict[str, object] = {
        "APP_ENV": "development",
        "APP_HOST": "127.0.0.1",
        "APP_PORT": "8000",
        "DATABASE_URL": (
            "postgresql+psycopg://company_system_dev:local-only@127.0.0.1/"
            "company_system_dev"
        ),
    }
    values.update(overrides)
    return values


def database_url_for(
    environment: str,
    database_name: str,
    *,
    password: str = "local-only",
) -> str:
    """Build a DSN whose username belongs to the requested environment."""

    marker = {
        "development": "dev",
        "test": "test",
        "production": "prod",
    }[environment]
    return (
        f"postgresql+psycopg://company_system_{marker}:{password}"
        f"@database.internal/{database_name}"
    )


def make_test_settings() -> AppSettings:
    """Build validated settings that can never identify a development DB."""

    return AppSettings.model_validate(
        valid_settings_values(
            APP_ENV="test",
            DATABASE_URL=(
                "postgresql+psycopg://company_system_test:test-only@127.0.0.1/"
                "company_system_test"
            ),
        )
    )
