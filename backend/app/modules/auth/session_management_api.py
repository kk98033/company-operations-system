"""HTTP API for personal and organization-scoped Session management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session as OrmSession

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.cookies import clear_auth_cookies
from app.modules.auth.dependencies import require_authenticated_csrf, require_current_session
from app.modules.auth.schemas import (
    AuthenticatedUserResponse,
    ManagedSessionListResponse,
    ManagedSessionResponse,
    MembershipSessionRevocationRequest,
    SessionRevocationRequest,
)
from app.modules.auth.services import (
    AuthenticatedSession,
    ManagedSession,
    list_company_sessions,
    list_personal_sessions,
    revoke_managed_session,
    revoke_membership_sessions,
)
from app.modules.authorization import require_capability

_manage_sessions = require_capability("sessions.manage")


def _response(item: ManagedSession, *, current_session_id: UUID | None) -> ManagedSessionResponse:
    return ManagedSessionResponse(
        id=item.id,
        organization_member_id=item.organization_member_id,
        user=AuthenticatedUserResponse(
            id=item.user_id,
            login_name=item.login_name,
            display_name=item.display_name,
        ),
        client_summary=item.client_summary,
        created_at=item.created_at,
        expires_at=item.expires_at,
        revoked_at=item.revoked_at,
        status=item.status,
        is_current=item.id == current_session_id,
    )


def _list_response(
    items: list[ManagedSession],
    *,
    current_session_id: UUID | None,
) -> ManagedSessionListResponse:
    return ManagedSessionListResponse(
        items=[_response(item, current_session_id=current_session_id) for item in items],
        total_items=len(items),
    )


def _not_found() -> ApplicationError:
    return ApplicationError(
        status_code=404,
        code="SESSION_NOT_FOUND",
        message="找不到指定的登入工作階段",
    )


def build_session_management_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.get(
        "/sessions",
        response_model=ManagedSessionListResponse,
        operation_id="auth_list_personal_sessions",
        summary="列出自己的登入工作階段",
    )
    def personal_sessions(
        context: Annotated[AuthenticatedSession, Depends(require_current_session)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> ManagedSessionListResponse:
        return _list_response(
            list_personal_sessions(database_session, context=context, limit=limit),
            current_session_id=context.session_id,
        )

    @router.get(
        "/company-sessions",
        response_model=ManagedSessionListResponse,
        operation_id="auth_list_company_sessions",
        summary="列出目前公司尚未撤銷的登入工作階段",
    )
    def company_sessions(
        context: Annotated[AuthenticatedSession, Depends(_manage_sessions)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> ManagedSessionListResponse:
        return _list_response(
            list_company_sessions(database_session, context=context, limit=limit),
            current_session_id=context.session_id,
        )

    @router.post(
        "/company-sessions/{session_id}/revoke",
        status_code=status.HTTP_204_NO_CONTENT,
        operation_id="auth_revoke_company_session",
        summary="撤銷目前公司的一個登入工作階段",
    )
    def revoke_company_session(
        session_id: UUID,
        payload: SessionRevocationRequest,
        request: Request,
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        context: Annotated[AuthenticatedSession, Depends(_manage_sessions)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> Response:
        if not revoke_managed_session(
            database_session,
            context=context,
            target_session_id=session_id,
            reason=payload.reason,
            request_id=require_request_id(request),
        ):
            raise _not_found()
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        if session_id == context.session_id:
            clear_auth_cookies(response, settings=request.app.state.settings)
        return response

    @router.post(
        "/company-sessions/revoke-membership",
        status_code=status.HTTP_204_NO_CONTENT,
        operation_id="auth_revoke_membership_sessions",
        summary="撤銷公司成員的全部登入工作階段",
    )
    def revoke_all_membership_sessions(
        payload: MembershipSessionRevocationRequest,
        request: Request,
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        context: Annotated[AuthenticatedSession, Depends(_manage_sessions)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> Response:
        count = revoke_membership_sessions(
            database_session,
            context=context,
            target_membership_id=payload.organization_member_id,
            reason=payload.reason,
            request_id=require_request_id(request),
        )
        if count is None:
            raise _not_found()
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        if payload.organization_member_id == context.organization_member_id:
            clear_auth_cookies(response, settings=request.app.state.settings)
        return response

    return router
