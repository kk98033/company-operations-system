"""HTTP endpoints for login and opaque server-side sessions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr
from sqlalchemy.orm import Session as OrmSession

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.modules.auth.errors import (
    AuthenticationFailedError,
    SessionCreationError,
)
from app.modules.auth.schemas import (
    AuthenticatedOrganizationResponse,
    AuthenticatedUserResponse,
    LoginRequest,
    LoginResponse,
)
from app.modules.auth.services import (
    create_login_session,
    revoke_session,
)
from app.modules.auth.tokens import is_session_token_format

_bearer = HTTPBearer(auto_error=False, scheme_name="SessionBearer")
_AUTH_CHALLENGE = {"WWW-Authenticate": 'Bearer realm="company-system"'}


def _authentication_error(*, session_invalid: bool = False) -> ApplicationError:
    return ApplicationError(
        status_code=401,
        code="SESSION_INVALID" if session_invalid else "AUTHENTICATION_FAILED",
        message=(
            "登入狀態已失效"
            if session_invalid
            else "登入資料不正確或帳號目前無法使用"
        ),
        headers=_AUTH_CHALLENGE,
    )


def _require_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer),
    ],
) -> SecretStr:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not is_session_token_format(credentials.credentials)
    ):
        raise _authentication_error(session_invalid=True)
    return SecretStr(credentials.credentials)


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post(
        "/login",
        response_model=LoginResponse,
        operation_id="auth_login",
        summary="以使用者代號建立伺服器登入 Session",
    )
    def login(
        payload: LoginRequest,
        response: Response,
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> LoginResponse:
        try:
            result = create_login_session(
                database_session,
                login_name=payload.login_name,
                password=payload.password,
                organization_id=payload.organization_id,
            )
        except AuthenticationFailedError:
            raise _authentication_error() from None
        except SessionCreationError:
            raise ApplicationError(
                status_code=500,
                code="SESSION_CREATION_FAILED",
                message="目前無法建立登入狀態",
            ) from None

        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return LoginResponse(
            session_token=result.raw_session_token.get_secret_value(),
            token_type="Bearer",
            expires_at=result.expires_at,
            user=AuthenticatedUserResponse(
                id=result.user_id,
                login_name=result.login_name,
                display_name=result.display_name,
            ),
            organization=AuthenticatedOrganizationResponse(
                id=result.organization_id,
                name=result.organization_name,
            ),
        )

    @router.post(
        "/logout",
        status_code=status.HTTP_204_NO_CONTENT,
        operation_id="auth_logout",
        summary="撤銷目前伺服器 Session",
    )
    def logout(
        raw_token: Annotated[SecretStr, Depends(_require_bearer_token)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> Response:
        revoke_session(database_session, raw_token=raw_token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
