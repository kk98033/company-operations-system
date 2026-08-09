"""Browser cookie contract for opaque Sessions and CSRF tokens."""

from __future__ import annotations

from fastapi import Response
from pydantic import SecretStr

from app.core.config import AppEnvironment, AppSettings
from app.modules.auth.csrf import derive_csrf_token

SESSION_COOKIE_NAME = "company_system_session"
CSRF_COOKIE_NAME = "company_system_csrf"
SESSION_COOKIE_PATH = "/api/v1"
CSRF_COOKIE_PATH = "/"


def _secure_cookie(settings: AppSettings) -> bool:
    return settings.environment is AppEnvironment.PRODUCTION


def set_auth_cookies(
    response: Response,
    *,
    raw_session_token: SecretStr,
    settings: AppSettings,
) -> None:
    """Set host-only browser-session cookies; the DB owns the eight-hour limit."""

    secure = _secure_cookie(settings)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_session_token.get_secret_value(),
        httponly=True,
        secure=secure,
        samesite="strict",
        path=SESSION_COOKIE_PATH,
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        derive_csrf_token(
            raw_session_token,
            signing_key=settings.csrf_hmac_key_value(),
        ).get_secret_value(),
        httponly=False,
        secure=secure,
        samesite="strict",
        path=CSRF_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response, *, settings: AppSettings) -> None:
    """Expire both cookies with the same policy and each cookie's original path."""

    secure = _secure_cookie(settings)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path=SESSION_COOKIE_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path=CSRF_COOKIE_PATH,
        secure=secure,
        httponly=False,
        samesite="strict",
    )
