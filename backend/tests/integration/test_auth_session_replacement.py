"""PostgreSQL acceptance tests for one active session per membership."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.cookies import SESSION_COOKIE_NAME
from app.modules.auth.models import LoginSecurityEvent, Session
from app.modules.auth.services import get_active_session
from app.modules.organizations.models import Organization, OrganizationMember
from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _payload(identity) -> dict[str, str]:
    return {
        "organization_id": str(identity.organization_id),
        "login_name": identity.login_name,
        "password": identity.password.get_secret_value(),
    }


def test_second_login_replaces_the_previous_session_and_records_both_sessions(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)

    first = client.post("/api/v1/auth/login", json=_payload(identity))
    first_token = SecretStr(first.cookies[SESSION_COOKIE_NAME])
    second = client.post("/api/v1/auth/login", json=_payload(identity))
    second_token = SecretStr(second.cookies[SESSION_COOKIE_NAME])

    assert first.status_code == 200
    assert second.status_code == 200
    assert first_token != second_token
    with OrmSession(identity_engine) as session:
        rows = session.scalars(select(Session).order_by(Session.created_at, Session.id)).all()
        old_context = get_active_session(session, raw_token=first_token)
        new_context = get_active_session(session, raw_token=second_token)
        events = session.execute(
            select(LoginSecurityEvent.event_type, LoginSecurityEvent.session_id)
        ).all()
    assert len(rows) == 2
    assert sum(row.revoked_at is None for row in rows) == 1
    assert old_context is None
    assert new_context is not None
    assert new_context.user_id == identity.user_id
    assert [event.event_type for event in events].count("login_succeeded") == 2
    assert [event.event_type for event in events].count("session_replaced") == 1
    assert {event.session_id for event in events if event.session_id is not None} == {
        row.id for row in rows
    }


def test_different_user_accounts_keep_independent_active_sessions(
    identity_engine: Engine,
) -> None:
    first_identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    second_identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)

    assert client.post("/api/v1/auth/login", json=_payload(first_identity)).status_code == 200
    assert client.post("/api/v1/auth/login", json=_payload(second_identity)).status_code == 200
    with identity_engine.connect() as connection:
        rows = connection.execute(select(Session.organization_member_id, Session.revoked_at)).all()
    assert {row.organization_member_id for row in rows} == {
        first_identity.membership_id,
        second_identity.membership_id,
    }
    assert all(row.revoked_at is None for row in rows)


def test_database_rejects_a_second_unrevoked_session_for_one_membership(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)
    assert client.post("/api/v1/auth/login", json=_payload(identity)).status_code == 200
    timestamp = datetime.now(UTC)

    with pytest.raises(IntegrityError):
        with identity_engine.begin() as connection:
            connection.execute(
                Session.__table__.insert(),
                {
                    "organization_member_id": identity.membership_id,
                    "token_digest": "a" * 64,
                    "created_at": timestamp,
                    "expires_at": timestamp + timedelta(hours=8),
                },
            )


def test_same_user_keeps_one_active_session_per_organization_membership(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    second_organization_id = uuid4()
    second_membership_id = uuid4()
    with identity_engine.begin() as connection:
        connection.execute(
            Organization.__table__.insert(),
            {"id": second_organization_id, "name": "Second Synthetic Organization"},
        )
        connection.execute(
            OrganizationMember.__table__.insert(),
            {
                "id": second_membership_id,
                "organization_id": second_organization_id,
                "user_id": identity.user_id,
            },
        )
    client = make_auth_client(identity_engine)

    first = client.post("/api/v1/auth/login", json=_payload(identity))
    second_payload = _payload(identity)
    second_payload["organization_id"] = str(second_organization_id)
    second = client.post("/api/v1/auth/login", json=second_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    with identity_engine.connect() as connection:
        memberships = connection.scalars(select(Session.organization_member_id)).all()
        active_count = connection.scalar(
            select(func.count()).select_from(Session).where(Session.revoked_at.is_(None))
        )
    assert set(memberships) == {identity.membership_id, second_membership_id}
    assert active_count == 2
