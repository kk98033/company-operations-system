"""HTTP endpoints for login and opaque server-side sessions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import SecretStr
from sqlalchemy.orm import Session as OrmSession

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.modules.auth.dependencies import (
    optional_logout_session,
    require_current_session,
    require_trusted_origin,
)
from app.modules.auth.errors import (
    AuthenticationFailedError,
    LoginRateLimitedError,
    SessionCreationError,
)
from app.modules.auth.schemas import (
    AuthenticatedOrganizationResponse,
    AuthenticatedUserResponse,
    CurrentSessionResponse,
    LoginRequest,
    LoginResponse,
)
from app.modules.auth.services import (
    AuthenticatedSession,
    create_login_session,
    revoke_session,
)
from app.modules.authorization import list_capabilities


def _authentication_error() -> ApplicationError:
    return ApplicationError(
        status_code=401,
        code="AUTHENTICATION_FAILED",
        message="登入資料不正確或帳號目前無法使用",
    )


def _session_response(
    context: AuthenticatedSession,
    database_session: OrmSession,
) -> CurrentSessionResponse:
    return CurrentSessionResponse(
        expires_at=context.expires_at,
        user=AuthenticatedUserResponse(
            id=context.user_id,
            login_name=context.login_name,
            display_name=context.display_name,
        ),
        organization=AuthenticatedOrganizationResponse(
            id=context.organization_id,
            name=context.organization_name,
        ),
        capabilities=list(
            list_capabilities(
                database_session,
                organization_member_id=context.organization_member_id,
                organization_id=context.organization_id,
            )
        ),
    )


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
        request: Request,
        response: Response,
        _trusted_origin: Annotated[None, Depends(require_trusted_origin)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> LoginResponse:
        try:
            result = create_login_session(
                database_session,
                login_name=payload.login_name,
                password=payload.password,
                organization_id=payload.organization_id,
                request_id=require_request_id(request),
                security_hmac_key=request.app.state.settings.auth_security_hmac_key_value(),
            )
        except AuthenticationFailedError:
            raise _authentication_error() from None
        except LoginRateLimitedError as exc:
            raise ApplicationError(
                status_code=429,
                code="LOGIN_RATE_LIMITED",
                message="登入嘗試過於頻繁，請稍後再試",
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from None
        except SessionCreationError:
            raise ApplicationError(
                status_code=500,
                code="SESSION_CREATION_FAILED",
                message="目前無法建立登入狀態",
            ) from None

        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        set_auth_cookies(
            response,
            raw_session_token=result.raw_session_token,
            settings=request.app.state.settings,
        )
        capabilities = list_capabilities(
            database_session,
            organization_member_id=result.organization_member_id,
            organization_id=result.organization_id,
        )
        return LoginResponse(
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
            capabilities=list(capabilities),
        )

    @router.get(
        "/session",
        response_model=CurrentSessionResponse,
        operation_id="auth_current_session",
        summary="載入目前使用者與公司 Session",
    )
    def current_session(
        response: Response,
        context: Annotated[AuthenticatedSession, Depends(require_current_session)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CurrentSessionResponse:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return _session_response(context, database_session)

    @router.post(
        "/logout",
        status_code=status.HTTP_204_NO_CONTENT,
        operation_id="auth_logout",
        summary="撤銷目前伺服器 Session",
    )
    def logout(
        request: Request,
        raw_token: Annotated[SecretStr | None, Depends(optional_logout_session)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> Response:
        if raw_token is not None:
            revoke_session(database_session, raw_token=raw_token)
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response, settings=request.app.state.settings)
        return response

    return router
