"""Transactional login throttle state and security-event operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.login_security import (
    LOGIN_BLOCK_DURATION,
    LOGIN_FAILURE_LIMIT,
    LOGIN_FAILURE_WINDOW,
    advisory_lock_key,
)
from app.modules.auth.models import LoginSecurityEvent, LoginThrottleState


def lock_login_bucket(session: OrmSession, fingerprint: str) -> None:
    """Serialize one opaque bucket for the current database transaction."""

    session.execute(
        select(func.pg_advisory_xact_lock(advisory_lock_key(fingerprint)))
    )


def active_blocked_until(
    throttle: LoginThrottleState | None,
    *,
    timestamp: datetime,
) -> datetime | None:
    """Return only a block that has not expired."""

    if (
        throttle is not None
        and throttle.blocked_until is not None
        and throttle.blocked_until > timestamp
    ):
        return throttle.blocked_until
    return None


def record_login_event(
    session: OrmSession,
    *,
    event_type: str,
    fingerprint: str,
    request_id: UUID,
    timestamp: datetime,
    session_id: UUID | None = None,
    failure_count: int | None = None,
    blocked_until: datetime | None = None,
) -> None:
    """Stage one append-only privacy-preserving security event."""

    session.add(
        LoginSecurityEvent(
            event_type=event_type,
            credential_fingerprint=fingerprint,
            request_id=request_id,
            session_id=session_id,
            failure_count=failure_count,
            blocked_until=blocked_until,
            created_at=timestamp,
        )
    )


def record_failed_login(
    session: OrmSession,
    *,
    throttle: LoginThrottleState | None,
    fingerprint: str,
    request_id: UUID,
    timestamp: datetime,
) -> datetime | None:
    """Increment or reset one failure window and return a new block, if any."""

    window_expired = throttle is not None and (
        throttle.blocked_until is not None
        or timestamp - throttle.window_started_at >= LOGIN_FAILURE_WINDOW
    )
    if throttle is None:
        throttle = LoginThrottleState(
            credential_fingerprint=fingerprint,
            failure_count=1,
            window_started_at=timestamp,
            last_failed_at=timestamp,
        )
        session.add(throttle)
    elif window_expired:
        throttle.failure_count = 1
        throttle.window_started_at = timestamp
        throttle.last_failed_at = timestamp
        throttle.blocked_until = None
        throttle.updated_at = timestamp
    else:
        throttle.failure_count += 1
        throttle.last_failed_at = timestamp
        throttle.updated_at = timestamp

    if throttle.failure_count >= LOGIN_FAILURE_LIMIT:
        throttle.blocked_until = timestamp + LOGIN_BLOCK_DURATION
    record_login_event(
        session,
        event_type=(
            "login_rate_limited"
            if throttle.blocked_until is not None
            else "login_failed"
        ),
        fingerprint=fingerprint,
        request_id=request_id,
        failure_count=throttle.failure_count,
        blocked_until=throttle.blocked_until,
        timestamp=timestamp,
    )
    return throttle.blocked_until


def clear_login_throttle(
    session: OrmSession,
    throttle: LoginThrottleState | None,
) -> int:
    """Remove mutable failure state and return its prior count."""

    if throttle is None:
        return 0
    failure_count = throttle.failure_count
    session.delete(throttle)
    return failure_count
