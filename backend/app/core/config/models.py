"""Typed application settings shared by startup and infrastructure code."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class AppEnvironment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class AppSettings(BaseModel):
    """Validated process settings with environment-variable aliases."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    environment: AppEnvironment = Field(alias="APP_ENV")
    host: str = Field(alias="APP_HOST", min_length=1)
    port: int = Field(alias="APP_PORT", ge=1, le=65535)
    database_url: SecretStr = Field(alias="DATABASE_URL", min_length=1)

    @model_validator(mode="after")
    def validate_database_environment(self) -> AppSettings:
        """Protect every validated settings object, including injected ones."""

        from app.core.config.database_guard import validate_database_target

        validate_database_target(
            environment=self.environment.value,
            database_url=self.database_url.get_secret_value(),
        )
        return self

    def database_url_value(self) -> str:
        """Return the DSN only for code that must establish a connection."""

        return self.database_url.get_secret_value()
