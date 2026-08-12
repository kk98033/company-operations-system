"""Reusable Cookie authentication dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, Request, Security
from fastapi.security import APIKeyCookie
from pydantic import SecretStr
from sqlalchemy.orm import Session as OrmSession

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.modules.auth.cookies import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from app.modules.auth.request_security import (
    browser_security_error,
    cookie_values,
    require_bound_csrf,
    require_trusted_origin,
)
from app.modules.auth.services import AuthenticatedSession, get_active_session
from app.modules.auth.tokens import is_session_token_format

_session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="SessionCookie",
    auto_error=False,
)


def authentication_error() -> ApplicationError:
    return ApplicationError(
        status_code=401,
        code="SESSION_INVALID",
        message="登入狀態已失效",
    )


def require_session_cookie(
    request: Request,
    raw_value: Annotated[str | None, Security(_session_cookie)],
) -> SecretStr:
    """Load one well-formed opaque token from the HttpOnly cookie."""

    values = cookie_values(request, SESSION_COOKIE_NAME)
    if (
        raw_value is None
        or len(values) != 1
        or values[0] != raw_value
        or not is_session_token_format(raw_value)
    ):
        raise authentication_error()
    return SecretStr(raw_value)


def require_current_session(
    raw_session_token: Annotated[SecretStr, Depends(require_session_cookie)],
    database_session: Annotated[OrmSession, Depends(get_database_session)],
) -> AuthenticatedSession:
    """Resolve the Cookie into one currently active identity context."""

    context = get_active_session(database_session, raw_token=raw_session_token)
    if context is None:
        raise authentication_error()
    return context


def require_authenticated_csrf(
    request: Request,
    raw_session_token: Annotated[SecretStr, Depends(require_session_cookie)],
) -> None:
    """Protect an authenticated state-changing browser request."""

    require_trusted_origin(request)
    require_bound_csrf(request, raw_session_token=raw_session_token)


def optional_logout_session(
    request: Request,
    raw_value: Annotated[str | None, Security(_session_cookie)],
    _csrf_cookie_contract: Annotated[
        str | None,
        Cookie(alias=CSRF_COOKIE_NAME),
    ] = None,
    _csrf_header_contract: Annotated[
        str | None,
        Header(alias="X-CSRF-Token"),
    ] = None,
) -> SecretStr | None:
    """Validate origin first; require CSRF only when a usable Cookie exists."""

    require_trusted_origin(request)
    session_cookies = cookie_values(request, SESSION_COOKIE_NAME)
    if len(session_cookies) > 1:
        raise browser_security_error()
    if (
        raw_value is None
        or len(session_cookies) != 1
        or session_cookies[0] != raw_value
        or not is_session_token_format(raw_value)
    ):
        return None
    raw_session_token = SecretStr(raw_value)
    require_bound_csrf(
        request,
        raw_session_token=raw_session_token,
    )
    return raw_session_token
