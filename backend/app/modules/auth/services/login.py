"""Credential verification and atomic login session creation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.errors import (
    AuthenticationFailedError,
    LoginRateLimitedError,
    SessionCreationError,
)
from app.modules.auth.login_security import derive_login_fingerprint, retry_after_seconds
from app.modules.auth.models import (
    LoginThrottleState,
    Session,
    User,
)
from app.modules.auth.passwords import hash_password, verify_password
from app.modules.auth.services.login_throttle import (
    active_blocked_until,
    clear_login_throttle,
    lock_login_bucket,
    record_failed_login,
    record_login_event,
)
from app.modules.auth.tokens import IssuedSessionToken, issue_session_token
from app.modules.organizations.models import Organization, OrganizationMember

DEFAULT_SESSION_TTL = timedelta(hours=8)
_DUMMY_PASSWORD = SecretStr("not-a-real-account-password-check-only")
_DUMMY_PASSWORD_HASH = hash_password(_DUMMY_PASSWORD)


@dataclass(frozen=True, slots=True)
class LoginResult:
    raw_session_token: SecretStr
    expires_at: datetime
    organization_member_id: UUID
    user_id: UUID
    login_name: str
    display_name: str
    organization_id: UUID
    organization_name: str
    session_id: UUID | None = None


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
    request_id: UUID,
    security_hmac_key: bytes,
    client_summary: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    token_issuer: Callable[[], IssuedSessionToken] = issue_session_token,
    session_ttl: timedelta = DEFAULT_SESSION_TTL,
) -> LoginResult:
    """Authenticate, throttle, and persist security evidence atomically."""

    authentication_failed = False
    rate_limited_until: datetime | None = None

    try:
        with session.begin():
            normalized_login_bucket = session.scalar(
                select(func.lower(func.btrim(login_name)))
            )
            assert normalized_login_bucket is not None
            fingerprint = derive_login_fingerprint(
                organization_id=organization_id,
                normalized_login_bucket=normalized_login_bucket,
                signing_key=security_hmac_key,
            )
            lock_login_bucket(session, fingerprint)
            timestamp = now()
            throttle = session.get(LoginThrottleState, fingerprint)
            rate_limited_until = active_blocked_until(
                throttle,
                timestamp=timestamp,
            )
            if rate_limited_until is not None:
                assert throttle is not None
                record_login_event(
                    session,
                    event_type="login_rate_limited",
                    fingerprint=fingerprint,
                    request_id=request_id,
                    failure_count=throttle.failure_count,
                    blocked_until=rate_limited_until,
                    timestamp=timestamp,
                )
                candidate = None
            else:
                candidate = _find_login_candidate(
                    session,
                    login_name=login_name,
                    organization_id=organization_id,
                )
            if rate_limited_until is None:
                if candidate is None:
                    user = membership = organization = None
                    password_hash = _DUMMY_PASSWORD_HASH
                else:
                    membership, organization, user = candidate
                    password_hash = user.password_hash
                password_matches = verify_password(password, password_hash)
                authentication_failed = (
                    user is None
                    or not password_matches
                    or user.status != "active"
                    or membership is None
                    or membership.status != "active"
                    or organization is None
                    or organization.status != "active"
                )
                if authentication_failed:
                    rate_limited_until = record_failed_login(
                        session,
                        throttle=throttle,
                        fingerprint=fingerprint,
                        request_id=request_id,
                        timestamp=timestamp,
                    )
                else:
                    previous_failures = clear_login_throttle(session, throttle)
                    locked_membership_id = session.scalar(
                        select(OrganizationMember.id)
                        .where(OrganizationMember.id == membership.id)
                        .with_for_update()
                    )
                    assert locked_membership_id == membership.id
                    session_timestamp = now()
                    replaced_session_ids = session.scalars(
                        update(Session)
                        .where(
                            Session.organization_member_id == membership.id,
                            Session.revoked_at.is_(None),
                        )
                        .values(revoked_at=session_timestamp)
                        .returning(Session.id)
                    ).all()
                    expires_at = session_timestamp + session_ttl
                    issued_token = token_issuer()
                    new_session_id = uuid4()
                    session.add(
                        Session(
                            id=new_session_id,
                            organization_member_id=membership.id,
                            token_digest=issued_token.digest,
                            client_summary=client_summary,
                            created_at=session_timestamp,
                            expires_at=expires_at,
                        )
                    )
                    session.flush()
                    for replaced_session_id in replaced_session_ids:
                        record_login_event(
                            session,
                            event_type="session_replaced",
                            fingerprint=fingerprint,
                            request_id=request_id,
                            session_id=replaced_session_id,
                            timestamp=session_timestamp,
                        )
                    record_login_event(
                        session,
                        event_type="login_succeeded",
                        fingerprint=fingerprint,
                        request_id=request_id,
                        session_id=new_session_id,
                        failure_count=previous_failures,
                        timestamp=session_timestamp,
                    )
                    user.last_login_at = session_timestamp
    except IntegrityError:
        raise SessionCreationError from None

    if rate_limited_until is not None:
        raise LoginRateLimitedError(
            retry_after_seconds(
                blocked_until=rate_limited_until,
                timestamp=timestamp,
            )
        )
    if authentication_failed:
        raise AuthenticationFailedError

    return LoginResult(
        raw_session_token=issued_token.raw,
        expires_at=expires_at,
        organization_member_id=membership.id,
        user_id=user.id,
        login_name=user.login_name,
        display_name=user.display_name,
        organization_id=organization.id,
        organization_name=organization.name,
        session_id=new_session_id,
    )
