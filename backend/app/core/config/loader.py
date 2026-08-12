"""Deterministic settings loading from a local dotenv file and the process."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import ValidationError

from app.core.config.models import AppSettings

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
_REQUIRED_VARIABLES = (
    "APP_ENV",
    "APP_HOST",
    "APP_PORT",
    "DATABASE_URL",
    "APP_PUBLIC_ORIGIN",
    "CSRF_HMAC_KEY",
    "AUTH_SECURITY_HMAC_KEY",
)


class SettingsLoadError(RuntimeError):
    """Safe startup error containing no environment variable values."""


def _source_values(
    *,
    environ: Mapping[str, Any] | None,
    env_file: Path | None,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if env_file is not None and env_file.is_file():
        values.update(
            {
                key: value
                for key, value in dotenv_values(env_file).items()
                if value is not None
            }
        )
    values.update(os.environ if environ is None else environ)
    return values


def _missing_variables(values: Mapping[str, Any]) -> list[str]:
    return [name for name in _REQUIRED_VARIABLES if not values.get(name)]


def load_settings(
    *,
    environ: Mapping[str, Any] | None = None,
    env_file: Path | None = DEFAULT_ENV_FILE,
) -> AppSettings:
    """Load, validate and guard settings before the application can start."""

    values = _source_values(environ=environ, env_file=env_file)
    missing_variables = _missing_variables(values)
    if missing_variables:
        joined_names = ", ".join(missing_variables)
        raise SettingsLoadError(f"缺少必要環境變數: {joined_names}")

    try:
        settings = AppSettings.model_validate(values)
    except ValidationError as exc:
        raise SettingsLoadError(f"環境設定無效: {exc}") from None

    return settings
