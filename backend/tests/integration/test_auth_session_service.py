"""PostgreSQL-backed acceptance tests for session resolution and logout."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.cookies import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from app.modules.auth.csrf import derive_csrf_token
from app.modules.auth.errors import SessionCreationError
from app.modules.auth.models import LoginSecurityEvent, Session, User
from app.modules.auth.services import (
    create_login_session,
    get_active_session,
)
from app.modules.auth.tokens import IssuedSessionToken, digest_session_token
from app.modules.organizations.models import Organization, OrganizationMember
from tests.integration.auth_test_support import create_auth_identity, make_auth_client
from tests.settings_factory import make_test_settings

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _login(identity_engine: Engine, identity, *, now: datetime | None = None):
    timestamp = now or datetime.now(UTC)
    with OrmSession(identity_engine) as session:
        return create_login_session(
            session,
            login_name=identity.login_name,
            password=identity.password,
            organization_id=identity.organization_id,
            request_id=uuid4(),
            security_hmac_key=make_test_settings().auth_security_hmac_key_value(),
            now=lambda: timestamp,
        )


def _logout(client, raw_token: SecretStr):
    csrf_token = derive_csrf_token(
        raw_token,
        signing_key=make_test_settings().csrf_hmac_key_value(),
    ).get_secret_value()
    client.cookies.set(
        SESSION_COOKIE_NAME,
        raw_token.get_secret_value(),
        path="/api/v1",
    )
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token, path="/")
    return client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )


def test_logout_is_idempotent_and_invalidates_the_old_session(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    result = _login(identity_engine, identity)
    raw_token = result.raw_session_token
    client = make_auth_client(identity_engine)

    with OrmSession(identity_engine) as session:
        active_context = get_active_session(session, raw_token=raw_token)
    first = _logout(client, raw_token)
    with identity_engine.connect() as connection:
        first_revoked_at = connection.scalar(select(Session.revoked_at))
    second = _logout(client, raw_token)
    with identity_engine.connect() as connection:
        second_revoked_at = connection.scalar(select(Session.revoked_at))
    with OrmSession(identity_engine) as session:
        resolved = get_active_session(session, raw_token=raw_token)
        logout_events = session.scalars(
            select(LoginSecurityEvent).where(
                LoginSecurityEvent.event_type == "logout_succeeded"
            )
        ).all()

    assert first.status_code == 204
    assert second.status_code == 204
    assert active_context is not None
    assert active_context.user_id == identity.user_id
    assert active_context.organization_id == identity.organization_id
    assert first_revoked_at is not None
    assert second_revoked_at == first_revoked_at
    assert resolved is None
    assert len(logout_events) == 1
    assert logout_events[0].session_id == active_context.session_id
    assert logout_events[0].credential_fingerprint is None


def test_unknown_well_formed_token_has_the_same_logout_result(
    identity_engine: Engine,
) -> None:
    unknown_token = token_urlsafe(32)
    response = _logout(
        make_auth_client(identity_engine),
        SecretStr(unknown_token),
    )

    assert response.status_code == 204
    assert response.content == b""


def test_expired_token_has_the_same_logout_result_and_resolver_rejects_unknown(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    result = _login(
        identity_engine,
        identity,
        now=datetime.now(UTC) - timedelta(hours=9),
    )
    response = _logout(make_auth_client(identity_engine), result.raw_session_token)
    unknown_token = SecretStr(token_urlsafe(32))
    with OrmSession(identity_engine) as session:
        assert get_active_session(session, raw_token=unknown_token) is None
        assert get_active_session(session, raw_token=SecretStr("malformed")) is None

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.parametrize(
    "inactive_target",
    ["organization", "user", "membership"],
)
def test_resolver_rejects_session_when_any_identity_boundary_is_inactive(
    identity_engine: Engine,
    inactive_target: str,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    result = _login(identity_engine, identity)
    table, row_id = {
        "organization": (Organization, identity.organization_id),
        "user": (User, identity.user_id),
        "membership": (OrganizationMember, identity.membership_id),
    }[inactive_target]
    with OrmSession(identity_engine) as session:
        with session.begin():
            row = session.get(table, row_id)
            assert row is not None
            row.status = "inactive"
    with OrmSession(identity_engine) as session:
        assert get_active_session(session, raw_token=result.raw_session_token) is None


def test_resolver_rejects_token_at_the_exact_expiry_boundary(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    created_at = datetime.now(UTC)
    result = _login(identity_engine, identity, now=created_at)

    with OrmSession(identity_engine) as session:
        assert (
            get_active_session(
                session,
                raw_token=result.raw_session_token,
                now=lambda: created_at + timedelta(hours=8),
            )
            is None
        )


def test_digest_collision_rolls_back_last_login_and_new_session(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    raw_token = SecretStr(token_urlsafe(32))
    issued = IssuedSessionToken(
        raw=raw_token,
        digest=digest_session_token(raw_token),
    )
    with identity_engine.begin() as connection:
        connection.execute(
            Session.__table__.insert(),
            {
                "organization_member_id": identity.membership_id,
                "token_digest": issued.digest,
                "created_at": datetime.now(UTC),
                "expires_at": datetime.now(UTC) + timedelta(hours=8),
            },
        )

    with OrmSession(identity_engine) as session:
        with pytest.raises(SessionCreationError):
            create_login_session(
                session,
                login_name=identity.login_name,
                password=identity.password,
                organization_id=identity.organization_id,
                request_id=uuid4(),
                security_hmac_key=make_test_settings().auth_security_hmac_key_value(),
                token_issuer=lambda: issued,
            )

    with identity_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Session)) == 1
        assert connection.scalar(select(Session.revoked_at)) is None
        assert (
            connection.scalar(select(User.last_login_at).where(User.id == identity.user_id)) is None
        )
