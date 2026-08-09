"""Credential verification and atomic login session creation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.errors import (
    AuthenticationFailedError,
    SessionCreationError,
)
from app.modules.auth.models import Session, User
from app.modules.auth.passwords import hash_password, verify_password
from app.modules.auth.tokens import IssuedSessionToken, issue_session_token
from app.modules.organizations.models import Organization, OrganizationMember

DEFAULT_SESSION_TTL = timedelta(hours=8)
_DUMMY_PASSWORD = SecretStr("not-a-real-account-password-check-only")
_DUMMY_PASSWORD_HASH = hash_password(_DUMMY_PASSWORD)


@dataclass(frozen=True, slots=True)
class LoginResult:
    raw_session_token: SecretStr
    expires_at: datetime
    user_id: UUID
    login_name: str
    display_name: str
    organization_id: UUID
    organization_name: str


def _find_login_candidate(
    session: OrmSession,
    *,
    login_name: str,
    organization_id: UUID,
) -> tuple[OrganizationMember | None, Organization | None, User] | None:
    """Use one DB-normalized query for every credential outcome."""

    return session.execute(
        select(OrganizationMember, Organization)
        .select_from(User)
        .add_columns(User)
        .outerjoin(
            OrganizationMember,
            and_(
                OrganizationMember.user_id == User.id,
                OrganizationMember.organization_id == organization_id,
            ),
        )
        .outerjoin(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            func.lower(func.btrim(User.login_name))
            == func.lower(func.btrim(login_name))
        )
    ).one_or_none()


def create_login_session(
    session: OrmSession,
    *,
    login_name: str,
    password: SecretStr,
    organization_id: UUID,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    token_issuer: Callable[[], IssuedSessionToken] = issue_session_token,
    session_ttl: timedelta = DEFAULT_SESSION_TTL,
) -> LoginResult:
    """Authenticate and persist one digest-only session in one transaction."""

    try:
        with session.begin():
            candidate = _find_login_candidate(
                session,
                login_name=login_name,
                organization_id=organization_id,
            )
            if candidate is None:
                user = membership = organization = None
                password_hash = _DUMMY_PASSWORD_HASH
            else:
                membership, organization, user = candidate
                password_hash = user.password_hash
            password_matches = verify_password(password, password_hash)
            if (
                user is None
                or not password_matches
                or user.status != "active"
                or membership is None
                or membership.status != "active"
                or organization is None
                or organization.status != "active"
            ):
                raise AuthenticationFailedError

            timestamp = now()
            expires_at = timestamp + session_ttl
            issued_token = token_issuer()
            session.add(
                Session(
                    organization_member_id=membership.id,
                    token_digest=issued_token.digest,
                    created_at=timestamp,
                    expires_at=expires_at,
                )
            )
            user.last_login_at = timestamp
    except IntegrityError:
        raise SessionCreationError from None

    return LoginResult(
        raw_session_token=issued_token.raw,
        expires_at=expires_at,
        user_id=user.id,
        login_name=user.login_name,
        display_name=user.display_name,
        organization_id=organization.id,
        organization_name=organization.name,
    )
