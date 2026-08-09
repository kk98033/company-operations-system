"""Audit event application service owned by the caller's transaction."""

from __future__ import annotations

import re
from collections.abc import Mapping
from uuid import UUID, uuid4

from sqlalchemy.orm import Session as OrmSession

from app.modules.audit.models import AuditLog
from app.modules.audit.sanitizer import sanitize_audit_payload
from app.modules.organizations.scope import OrganizationScope

MAX_AUDIT_REASON_LENGTH = 1_000
_ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_ENTITY_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _optional_text(value: str | None, *, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must be nonblank and at most {maximum} characters")
    return normalized


def record_user_audit_event(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    request_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    document_number: str | None = None,
    event_status: str = "success",
    reason: str | None = None,
    before: Mapping[str, object] | None = None,
    after: Mapping[str, object] | None = None,
) -> AuditLog:
    """Stage one sanitized event without committing the business transaction."""

    if _ACTION_PATTERN.fullmatch(action) is None:
        raise ValueError("action must be a normalized capability-style code")
    if _ENTITY_TYPE_PATTERN.fullmatch(entity_type) is None:
        raise ValueError("entity_type must be normalized snake_case")
    if event_status not in {"success", "failure"}:
        raise ValueError("event_status must be success or failure")
    audit_log = AuditLog(
        id=uuid4(),
        organization_id=scope.organization_id,
        actor_kind="user",
        actor_membership_id=scope.organization_member_id,
        actor_user_id=scope.actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        document_number=_optional_text(
            document_number,
            field="document_number",
            maximum=128,
        ),
        event_status=event_status,
        reason=_optional_text(
            reason,
            field="reason",
            maximum=MAX_AUDIT_REASON_LENGTH,
        ),
        before_data=sanitize_audit_payload(before),
        after_data=sanitize_audit_payload(after),
        request_id=request_id,
    )
    session.add(audit_log)
    return audit_log
