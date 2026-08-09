"""Conservative audit payload sanitizer."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import SecretStr

REDACTED = "[REDACTED]"
TRUNCATED = "[TRUNCATED]"
UNSUPPORTED = "[UNSUPPORTED]"
MAX_AUDIT_DEPTH = 8
MAX_AUDIT_ITEMS = 100
MAX_AUDIT_STRING_LENGTH = 2_000
_SENSITIVE_MARKERS = (
    "api_key",
    "authorization",
    "cookie",
    "csrf",
    "file_content",
    "hash",
    "password",
    "private_key",
    "secret",
    "session",
    "token",
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(marker in normalized for marker in _SENSITIVE_MARKERS)


def _sanitize_value(value: Any, *, depth: int) -> object:
    if depth > MAX_AUDIT_DEPTH:
        return TRUNCATED
    if isinstance(value, (SecretStr, bytes, bytearray, memoryview)):
        return REDACTED
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, str):
        if len(value) <= MAX_AUDIT_STRING_LENGTH:
            return value
        return f"{value[:MAX_AUDIT_STRING_LENGTH]}{TRUNCATED}"
    if isinstance(value, (UUID, date, datetime, Decimal)):
        return str(value)
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for index, (raw_key, item) in enumerate(value.items()):
            if index >= MAX_AUDIT_ITEMS:
                sanitized[TRUNCATED] = TRUNCATED
                break
            key = str(raw_key)
            sanitized[key] = (
                REDACTED
                if _is_sensitive_key(key)
                else _sanitize_value(item, depth=depth + 1)
            )
        return sanitized
    if isinstance(value, Sequence):
        return [
            _sanitize_value(item, depth=depth + 1)
            for item in value[:MAX_AUDIT_ITEMS]
        ]
    return UNSUPPORTED


def sanitize_audit_payload(
    payload: Mapping[str, object] | None,
) -> dict[str, object] | None:
    """Return JSON-safe, size-bounded data with Secret fields removed."""

    if payload is None:
        return None
    return {
        key: (
            REDACTED
            if _is_sensitive_key(key)
            else _sanitize_value(value, depth=1)
        )
        for key, value in list(payload.items())[:MAX_AUDIT_ITEMS]
    }
