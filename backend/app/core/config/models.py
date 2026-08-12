"""Typed application settings shared by startup and infrastructure code."""

from __future__ import annotations

import base64
import re
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


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
    public_origin: str = Field(alias="APP_PUBLIC_ORIGIN", min_length=1)
    csrf_hmac_key: SecretStr = Field(alias="CSRF_HMAC_KEY", min_length=1)
    auth_security_hmac_key: SecretStr = Field(
        alias="AUTH_SECURITY_HMAC_KEY", min_length=1
    )

    @field_validator("public_origin")
    @classmethod
    def validate_public_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        try:
            parsed_port = parsed.port
        except ValueError:
            raise ValueError("APP_PUBLIC_ORIGIN port 格式無效") from None
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.hostname is None
            or "*" in parsed.netloc
            or "," in parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or (parsed_port is not None and not 1 <= parsed_port <= 65535)
        ):
            raise ValueError("APP_PUBLIC_ORIGIN 必須是單一完整 origin")
        return value.rstrip("/")

    @field_validator("csrf_hmac_key", "auth_security_hmac_key")
    @classmethod
    def validate_csrf_hmac_key(cls, value: SecretStr) -> SecretStr:
        raw_value = value.get_secret_value()
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", raw_value) is None:
            raise ValueError("HMAC key 必須是 32-byte base64url 密鑰")
        try:
            decoded = base64.urlsafe_b64decode(raw_value + "=")
        except (ValueError, TypeError):
            raise ValueError("HMAC key 格式無效") from None
        if len(decoded) != 32:
            raise ValueError("HMAC key 必須提供至少 256-bit 熵")
        return value

    @model_validator(mode="after")
    def validate_database_environment(self) -> AppSettings:
        """Protect every validated settings object, including injected ones."""

        from app.core.config.database_guard import validate_database_target

        validate_database_target(
            environment=self.environment.value,
            database_url=self.database_url.get_secret_value(),
        )
        if (
            self.environment is AppEnvironment.PRODUCTION
            and urlsplit(self.public_origin).scheme != "https"
        ):
            raise ValueError("production APP_PUBLIC_ORIGIN 必須使用 https")
        if (
            self.csrf_hmac_key.get_secret_value()
            == self.auth_security_hmac_key.get_secret_value()
        ):
            raise ValueError("AUTH_SECURITY_HMAC_KEY 必須與 CSRF_HMAC_KEY 不同")
        return self

    def database_url_value(self) -> str:
        """Return the DSN only for code that must establish a connection."""

        return self.database_url.get_secret_value()

    def csrf_hmac_key_value(self) -> bytes:
        """Return the CSRF signing key only at the HMAC boundary."""

        return base64.urlsafe_b64decode(self.csrf_hmac_key.get_secret_value() + "=")

    def auth_security_hmac_key_value(self) -> bytes:
        """Return the login fingerprint key only at the HMAC boundary."""

        return base64.urlsafe_b64decode(
            self.auth_security_hmac_key.get_secret_value() + "="
        )
