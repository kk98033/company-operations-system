"""Read-only HTTP endpoint for organization audit history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import PageParams, build_list_response
from app.core.database.session import get_database_session
from app.modules.audit.query import list_audit_logs
from app.modules.audit.schemas import (
    AuditFilterParams,
    AuditFilterSummary,
    AuditLogListResponse,
    AuditSortParams,
)
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.organizations.scope import OrganizationScope

_require_audit_read = require_capability("audit.read")


def build_audit_router() -> APIRouter:
    router = APIRouter(prefix="/audit-logs", tags=["audit"])

    @router.get(
        "",
        response_model=AuditLogListResponse,
        operation_id="audit_list",
        summary="查詢目前公司的不可變稽核紀錄",
    )
    def audit_list(
        page: Annotated[PageParams, Depends()],
        sort: Annotated[AuditSortParams, Depends()],
        filters: Annotated[AuditFilterParams, Depends()],
        context: Annotated[AuthenticatedSession, Depends(_require_audit_read)],
        database_session: Annotated[
            OrmSession,
            Depends(get_database_session),
        ],
    ) -> AuditLogListResponse:
        scope = OrganizationScope(
            organization_id=context.organization_id,
            organization_member_id=context.organization_member_id,
            actor_user_id=context.user_id,
        )
        items, total_items = list_audit_logs(
            database_session,
            scope=scope,
            page=page,
            sort=sort,
            filters=filters,
        )
        response = build_list_response(
            items=items,
            total_items=total_items,
            page=page,
            sort=sort,
            filters=AuditFilterSummary.model_validate(filters.model_dump()),
        )
        return AuditLogListResponse.model_validate(response)

    return router
