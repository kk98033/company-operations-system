"""Organization-scoped Session listing and audited remote revocation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit import record_user_audit_event
from app.modules.auth.models import Session, User
from app.modules.auth.services.security_events import record_authenticated_security_event
from app.modules.auth.services.session import AuthenticatedSession
from app.modules.organizations.models import OrganizationMember
from app.modules.organizations.scope import OrganizationScope

SessionStatus = Literal["active", "expired", "revoked", "identity_inactive"]


@dataclass(frozen=True, slots=True)
class ManagedSession:
    id: UUID
    organization_member_id: UUID
    user_id: UUID
    login_name: str
    display_name: str
    client_summary: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    status: SessionStatus


def _status(
    login_session: Session,
    membership: OrganizationMember,
    user: User,
    *,
    timestamp: datetime,
) -> SessionStatus:
    if login_session.revoked_at is not None:
        return "revoked"
    if login_session.expires_at <= timestamp:
        return "expired"
    if membership.status != "active" or user.status != "active":
        return "identity_inactive"
    return "active"


def _records(rows: list[tuple[Session, OrganizationMember, User]], now: datetime) -> list[ManagedSession]:
    return [
        ManagedSession(
            id=login_session.id,
            organization_member_id=membership.id,
            user_id=user.id,
            login_name=user.login_name,
            display_name=user.display_name,
            client_summary=login_session.client_summary or "未記錄裝置摘要",
            created_at=login_session.created_at,
            expires_at=login_session.expires_at,
            revoked_at=login_session.revoked_at,
            status=_status(login_session, membership, user, timestamp=now),
        )
        for login_session, membership, user in rows
    ]


def list_personal_sessions(
    session: OrmSession,
    *,
    context: AuthenticatedSession,
    limit: int = 50,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[ManagedSession]:
    rows = session.execute(
        select(Session, OrganizationMember, User)
        .join(OrganizationMember, OrganizationMember.id == Session.organization_member_id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(Session.organization_member_id == context.organization_member_id)
        .order_by(Session.created_at.desc(), Session.id.desc())
        .limit(limit)
    ).all()
    return _records(list(rows), now())


def list_company_sessions(
    session: OrmSession,
    *,
    context: AuthenticatedSession,
    limit: int = 100,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[ManagedSession]:
    timestamp = now()
    rows = session.execute(
        select(Session, OrganizationMember, User)
        .join(OrganizationMember, OrganizationMember.id == Session.organization_member_id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == context.organization_id,
            Session.revoked_at.is_(None),
            Session.expires_at > timestamp,
        )
        .order_by(Session.created_at.desc(), Session.id.desc())
        .limit(limit)
    ).all()
    return _records(list(rows), timestamp)


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        context.organization_id,
        context.organization_member_id,
        context.user_id,
    )


def revoke_managed_session(
    session: OrmSession,
    *,
    context: AuthenticatedSession,
    target_session_id: UUID,
    reason: str,
    request_id: UUID,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> bool:
    """Revoke one Session only when it belongs to the actor's company."""

    try:
        target = session.execute(
            select(Session)
            .join(OrganizationMember, OrganizationMember.id == Session.organization_member_id)
            .where(
                Session.id == target_session_id,
                OrganizationMember.organization_id == context.organization_id,
            )
            .with_for_update(of=Session)
        ).scalar_one_or_none()
        if target is None:
            session.rollback()
            return False
        changed = target.revoked_at is None
        if changed:
            target.revoked_at = now()
            record_user_audit_event(
                session,
                scope=_scope(context),
                request_id=request_id,
                action="session.revoke",
                entity_type="auth_session",
                entity_id=target.id,
                reason=reason,
                before={"status": "active"},
                after={"status": "revoked"},
            )
            record_authenticated_security_event(
                session,
                context=context,
                request_id=request_id,
                event_type="session_revoked",
                target_type="auth_session",
                target_id=target.id,
                timestamp=target.revoked_at,
            )
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise


def revoke_membership_sessions(
    session: OrmSession,
    *,
    context: AuthenticatedSession,
    target_membership_id: UUID,
    reason: str,
    request_id: UUID,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int | None:
    """Revoke every unrevoked Session for one membership in the actor's company."""

    try:
        membership = session.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.id == target_membership_id,
                OrganizationMember.organization_id == context.organization_id,
            )
            .with_for_update()
        )
        if membership is None:
            session.rollback()
            return None
        timestamp = now()
        revoked_ids = session.scalars(
            update(Session)
            .where(
                Session.organization_member_id == membership.id,
                Session.revoked_at.is_(None),
            )
            .values(revoked_at=timestamp)
            .returning(Session.id)
        ).all()
        record_user_audit_event(
            session,
            scope=_scope(context),
            request_id=request_id,
            action="session.revoke_all",
            entity_type="organization_member",
            entity_id=membership.id,
            reason=reason,
            before={"active_session_count": len(revoked_ids)},
            after={"active_session_count": 0},
        )
        record_authenticated_security_event(
            session,
            context=context,
            request_id=request_id,
            event_type="membership_sessions_revoked",
            target_type="organization_member",
            target_id=membership.id,
            timestamp=timestamp,
        )
        session.commit()
        return len(revoked_ids)
    except Exception:
        session.rollback()
        raise
