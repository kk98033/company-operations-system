"""Active-session resolution and idempotent revocation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.models import Session, User
from app.modules.auth.tokens import digest_session_token, is_session_token_format
from app.modules.organizations.models import Organization, OrganizationMember


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    expires_at: datetime
    user_id: UUID
    login_name: str
    display_name: str
    organization_id: UUID
    organization_name: str


def get_active_session(
    session: OrmSession,
    *,
    raw_token: SecretStr,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> AuthenticatedSession | None:
    """Resolve an opaque token while enforcing every active identity boundary."""

    raw_value = raw_token.get_secret_value()
    if not is_session_token_format(raw_value):
        return None
    row = session.execute(
        select(Session, OrganizationMember, User, Organization)
        .join(
            OrganizationMember,
            OrganizationMember.id == Session.organization_member_id,
        )
        .join(User, User.id == OrganizationMember.user_id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(Session.token_digest == digest_session_token(raw_token))
    ).one_or_none()
    if row is None:
        return None
    login_session, membership, user, organization = row
    if (
        login_session.revoked_at is not None
        or login_session.expires_at <= now()
        or membership.status != "active"
        or user.status != "active"
        or organization.status != "active"
    ):
        return None
    return AuthenticatedSession(
        expires_at=login_session.expires_at,
        user_id=user.id,
        login_name=user.login_name,
        display_name=user.display_name,
        organization_id=organization.id,
        organization_name=organization.name,
    )


def revoke_session(
    session: OrmSession,
    *,
    raw_token: SecretStr,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    """Revoke at most once; unknown and already-revoked tokens are no-ops."""

    raw_value = raw_token.get_secret_value()
    if not is_session_token_format(raw_value):
        return
    with session.begin():
        session.execute(
            update(Session)
            .where(
                Session.token_digest == digest_session_token(raw_token),
                Session.revoked_at.is_(None),
            )
            .values(revoked_at=now())
        )
