"""Bounded organization-scoped audit history queries."""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import PageParams, SortDirection
from app.modules.audit.models import AuditLog
from app.modules.audit.sanitizer import sanitize_audit_payload
from app.modules.audit.schemas import (
    AuditFilterParams,
    AuditLogResponse,
    AuditSortField,
    AuditSortParams,
)
from app.modules.organizations.scope import OrganizationScope


def _filtered_statement(
    scope: OrganizationScope,
    filters: AuditFilterParams,
) -> Select[tuple[AuditLog]]:
    statement = scope.constrain(select(AuditLog), model=AuditLog)
    if filters.keyword:
        keyword = filters.keyword
        statement = statement.where(
            or_(
                AuditLog.action.contains(keyword, autoescape=True),
                AuditLog.entity_type.contains(keyword, autoescape=True),
                AuditLog.document_number.contains(keyword, autoescape=True),
                AuditLog.reason.contains(keyword, autoescape=True),
            )
        )
    if filters.action:
        statement = statement.where(AuditLog.action == filters.action)
    if filters.entity_type:
        statement = statement.where(AuditLog.entity_type == filters.entity_type)
    if filters.request_id:
        statement = statement.where(AuditLog.request_id == filters.request_id)
    return statement


def list_audit_logs(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    page: PageParams,
    sort: AuditSortParams,
    filters: AuditFilterParams,
) -> tuple[list[AuditLogResponse], int]:
    """Return one safe page and its organization-scoped total count."""

    filtered = _filtered_statement(scope, filters)
    total_items = session.scalar(
        select(func.count()).select_from(filtered.subquery())
    ) or 0
    sort_column = {
        AuditSortField.CREATED_AT: AuditLog.created_at,
        AuditSortField.ACTION: AuditLog.action,
    }[sort.sort_by]
    direction = sort_column.asc if sort.sort_direction is SortDirection.ASC else sort_column.desc
    rows = session.scalars(
        filtered.order_by(direction(), AuditLog.id.desc())
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    items = [
        AuditLogResponse(
            id=row.id,
            actor_user_id=row.actor_user_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            document_number=row.document_number,
            event_status=row.event_status,
            reason=row.reason,
            before_data=sanitize_audit_payload(row.before_data),
            after_data=sanitize_audit_payload(row.after_data),
            request_id=row.request_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return items, total_items
