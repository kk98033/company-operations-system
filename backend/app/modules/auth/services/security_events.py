"""Append-only authenticated security-event recording."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.models import LoginSecurityEvent

if TYPE_CHECKING:
    from app.modules.auth.services.session import AuthenticatedSession

_TARGET_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def record_authenticated_security_event(
    session: OrmSession,
    *,
    context: AuthenticatedSession,
    request_id: UUID,
    event_type: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
    capability: str | None = None,
    timestamp: datetime | None = None,
) -> LoginSecurityEvent:
    """Stage one actor-linked security event in the caller's transaction."""

    if context.session_id is None:
        raise ValueError("authenticated security events require a session ID")
    if (target_type is None) != (target_id is None):
        raise ValueError("target_type and target_id must be provided together")
    if target_type is not None and _TARGET_PATTERN.fullmatch(target_type) is None:
        raise ValueError("target_type must be normalized snake_case")
    if capability is not None and _CAPABILITY_PATTERN.fullmatch(capability) is None:
        raise ValueError("capability must be a normalized capability code")

    event = LoginSecurityEvent(
        id=uuid4(),
        event_type=event_type,
        credential_fingerprint=None,
        request_id=request_id,
        organization_id=context.organization_id,
        actor_membership_id=context.organization_member_id,
        actor_user_id=context.user_id,
        session_id=context.session_id,
        failure_count=None,
        blocked_until=None,
        target_type=target_type,
        target_id=target_id,
        capability=capability,
        created_at=timestamp or datetime.now(UTC),
    )
    session.add(event)
    return event
