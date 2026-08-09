"""Opaque session token generation, validation, and one-way digesting."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from secrets import token_urlsafe

from pydantic import SecretStr

SESSION_TOKEN_BYTES = 32
SESSION_TOKEN_LENGTH = 43
_SESSION_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


@dataclass(frozen=True, slots=True)
class IssuedSessionToken:
    """Raw token returned once and its database-safe digest."""

    raw: SecretStr
    digest: str


def is_session_token_format(value: str) -> bool:
    """Accept only the exact opaque token shape issued by this service."""

    return _SESSION_TOKEN_PATTERN.fullmatch(value) is not None


def digest_session_token(raw_token: SecretStr) -> str:
    """Create the lowercase SHA-256 digest stored by the database."""

    return sha256(raw_token.get_secret_value().encode("utf-8")).hexdigest()


def issue_session_token(
    generator: Callable[[int], str] = token_urlsafe,
) -> IssuedSessionToken:
    """Generate one 256-bit opaque token and reject incompatible generators."""

    raw_value = generator(SESSION_TOKEN_BYTES)
    if not is_session_token_format(raw_value):
        raise RuntimeError("session token generator returned an invalid value")
    raw_token = SecretStr(raw_value)
    return IssuedSessionToken(
        raw=raw_token,
        digest=digest_session_token(raw_token),
    )
