"""Signed double-submit CSRF tokens bound to one server Session."""

from __future__ import annotations

import base64
from hashlib import sha256
from hmac import compare_digest, new

from pydantic import SecretStr

from app.modules.auth.tokens import digest_session_token

_CSRF_CONTEXT = b"csrf-v1\0"
CSRF_TOKEN_LENGTH = 43


def derive_csrf_token(
    raw_session_token: SecretStr,
    *,
    signing_key: bytes,
) -> SecretStr:
    """Sign the Session digest without exposing or persisting the raw token."""

    message = _CSRF_CONTEXT + digest_session_token(raw_session_token).encode("ascii")
    signature = new(signing_key, message, sha256).digest()
    encoded = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return SecretStr(encoded)


def csrf_token_matches(
    raw_session_token: SecretStr,
    *,
    signing_key: bytes,
    cookie_token: str,
    header_token: str,
) -> bool:
    """Require cookie, header, and server-signed Session binding to match."""

    if len(cookie_token) != CSRF_TOKEN_LENGTH or len(header_token) != CSRF_TOKEN_LENGTH:
        return False
    expected = derive_csrf_token(
        raw_session_token,
        signing_key=signing_key,
    ).get_secret_value()
    return compare_digest(cookie_token, header_token) and compare_digest(
        header_token,
        expected,
    )
