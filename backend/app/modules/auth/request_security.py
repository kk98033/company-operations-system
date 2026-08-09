"""Exact browser-origin and signed double-submit CSRF verification."""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from pydantic import SecretStr

from app.core.errors import ApplicationError
from app.modules.auth.csrf import csrf_token_matches


def browser_security_error() -> ApplicationError:
    """Return one non-oracular error for origin and CSRF failures."""

    return ApplicationError(
        status_code=403,
        code="CSRF_VALIDATION_FAILED",
        message="請求來源或驗證資訊無效",
    )


def _header_values(request: Request, name: str) -> list[str]:
    return request.headers.getlist(name)


def cookie_values(request: Request, name: str) -> list[str]:
    """Read all same-name Cookie values instead of trusting first-value folding."""

    values: list[str] = []
    for cookie_header in _header_values(request, "cookie"):
        for segment in cookie_header.split(";"):
            key, separator, value = segment.strip().partition("=")
            if separator and key == name:
                values.append(value)
    return values


def _referer_origin(value: str) -> str | None:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def require_trusted_origin(request: Request) -> None:
    """Require one exact configured Origin, with strict Referer fallback."""

    expected = request.app.state.settings.public_origin
    origins = _header_values(request, "origin")
    referers = _header_values(request, "referer")
    if len(origins) > 1 or len(referers) > 1:
        raise browser_security_error()

    if origins:
        origin = origins[0]
        if origin == "null" or "," in origin or origin != expected:
            raise browser_security_error()
        if referers and _referer_origin(referers[0]) != expected:
            raise browser_security_error()
        return

    if not referers or _referer_origin(referers[0]) != expected:
        raise browser_security_error()


def require_bound_csrf(
    request: Request,
    *,
    raw_session_token: SecretStr,
) -> None:
    """Validate CSRF cookie/header equality and its Session-bound signature."""

    csrf_cookies = cookie_values(request, "company_system_csrf")
    csrf_headers = _header_values(request, "x-csrf-token")
    if (
        len(csrf_cookies) != 1
        or len(csrf_headers) != 1
        or not csrf_token_matches(
            raw_session_token,
            signing_key=request.app.state.settings.csrf_hmac_key_value(),
            cookie_token=csrf_cookies[0],
            header_token=csrf_headers[0],
        )
    ):
        raise browser_security_error()
