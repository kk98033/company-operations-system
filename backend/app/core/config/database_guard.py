"""Safety rules preventing a process from targeting the wrong database."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

_POSTGRES_SCHEMES = frozenset({"postgres", "postgresql", "postgresql+psycopg"})
_ENVIRONMENT_DATABASE_MARKERS = {
    "development": re.compile(
        r"(?:^|[_-])dev(?:$|[_-])",
        re.IGNORECASE,
    ),
    "test": re.compile(
        r"(?:^|[_-])test(?:$|[_-])",
        re.IGNORECASE,
    ),
    "production": re.compile(
        r"(?:^|[_-])prod(?:$|[_-])",
        re.IGNORECASE,
    ),
}


class UnsafeDatabaseTargetError(ValueError):
    """Raised when a database URL violates an environment isolation rule."""


def _validate_environment_marker(
    *,
    environment: str,
    target_name: str,
    target_label: str,
) -> None:
    expected_marker = _ENVIRONMENT_DATABASE_MARKERS[environment]
    if not expected_marker.search(target_name):
        raise UnsafeDatabaseTargetError(
            f"{environment} 環境的{target_label}必須含有對應的獨立標記"
        )

    has_foreign_marker = any(
        marker.search(target_name)
        for marker_environment, marker in _ENVIRONMENT_DATABASE_MARKERS.items()
        if marker_environment != environment
    )
    if has_foreign_marker:
        raise UnsafeDatabaseTargetError(
            f"{environment} 環境的{target_label}不得含有其他環境標記"
        )


def validate_database_target(
    *,
    environment: str,
    database_url: str,
) -> None:
    """Validate the target without ever returning or logging the full DSN."""

    parsed_url = urlsplit(database_url)
    if parsed_url.scheme not in _POSTGRES_SCHEMES:
        raise UnsafeDatabaseTargetError(
            "DATABASE_URL 必須使用 PostgreSQL 連線格式"
        )

    database_name = unquote(parsed_url.path).strip("/")
    if not database_name:
        raise UnsafeDatabaseTargetError("DATABASE_URL 必須指定資料庫名稱")

    database_username = unquote(parsed_url.username or "")
    if not database_username:
        raise UnsafeDatabaseTargetError("DATABASE_URL 必須指定資料庫帳號")

    if not parsed_url.password:
        raise UnsafeDatabaseTargetError("DATABASE_URL 必須指定資料庫密碼")

    if parsed_url.password.startswith("replace-with-"):
        raise UnsafeDatabaseTargetError(
            "DATABASE_URL 仍使用範例密碼，請先更換本機專用密碼"
        )

    _validate_environment_marker(
        environment=environment,
        target_name=database_name,
        target_label="資料庫名稱",
    )
    _validate_environment_marker(
        environment=environment,
        target_name=database_username,
        target_label="資料庫帳號",
    )
