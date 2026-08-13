"""PostgreSQL-backed acceptance tests for login behavior."""

from __future__ import annotations

import os
from datetime import timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, event, func, select, update
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.cookies import SESSION_COOKIE_NAME
from app.modules.auth.models import Session, User
from app.modules.auth.passwords import hash_password
from app.modules.auth.services import login as login_service
from app.modules.organizations.models import Organization, OrganizationMember
from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _payload(identity, *, password: str | None = None) -> dict[str, str]:
    return {
        "organization_id": str(identity.organization_id),
        "login_name": f"  {identity.login_name.upper()}  ",
        "password": password or identity.password.get_secret_value(),
    }


def test_login_normalizes_name_and_persists_only_digest_atomically(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    response = make_auth_client(identity_engine).post(
        "/api/v1/auth/login",
        json=_payload(identity),
    )

    assert response.status_code == 200
    raw_token = response.cookies[SESSION_COOKIE_NAME]
    with OrmSession(identity_engine) as session:
        stored_session = session.scalars(select(Session)).one()
        stored_user = session.get(User, identity.user_id)
        assert stored_user is not None

    assert stored_session.token_digest == sha256(raw_token.encode()).hexdigest()
    assert stored_session.token_digest != raw_token
    assert stored_session.last_seen_at is None
    assert stored_session.organization_member_id == identity.membership_id
    assert stored_user.last_login_at == stored_session.created_at
    assert stored_session.expires_at - stored_session.created_at == timedelta(hours=8)
    assert stored_user.password_hash == identity.password_hash
    assert response.headers["cache-control"] == "no-store"
    assert "session_token" not in response.json()
    assert "token_type" not in response.json()
    assert identity.password.get_secret_value() not in response.text


def test_each_successful_login_creates_a_distinct_active_session(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)

    first = client.post("/api/v1/auth/login", json=_payload(identity))
    second = client.post("/api/v1/auth/login", json=_payload(identity))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.cookies[SESSION_COOKIE_NAME] != second.cookies[SESSION_COOKIE_NAME]
    with identity_engine.connect() as connection:
        digests = connection.scalars(select(Session.token_digest)).all()
    assert len(digests) == 2
    assert len(set(digests)) == 2


def test_login_binds_the_explicit_membership_for_a_multi_organization_user(
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
            {
                "id": second_organization_id,
                "name": "Second Synthetic Organization",
            },
        )
        connection.execute(
            OrganizationMember.__table__.insert(),
            {
                "id": second_membership_id,
                "organization_id": second_organization_id,
                "user_id": identity.user_id,
            },
        )
    payload = _payload(identity)
    payload["organization_id"] = str(second_organization_id)

    response = make_auth_client(identity_engine).post(
        "/api/v1/auth/login",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["organization"]["id"] == str(second_organization_id)
    with identity_engine.connect() as connection:
        assert connection.scalar(select(Session.organization_member_id)) == (second_membership_id)


def test_database_normalization_keeps_tab_wrapped_login_distinct(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    tab_user_id = uuid4()
    tab_membership_id = uuid4()
    tab_password = SecretStr(token_urlsafe(24))
    tab_login_name = f"\t{identity.login_name}\t"
    with identity_engine.begin() as connection:
        connection.execute(
            User.__table__.insert(),
            {
                "id": tab_user_id,
                "login_name": tab_login_name,
                "display_name": "Tab Wrapped Synthetic User",
                "password_hash": hash_password(tab_password),
            },
        )
        connection.execute(
            OrganizationMember.__table__.insert(),
            {
                "id": tab_membership_id,
                "organization_id": identity.organization_id,
                "user_id": tab_user_id,
            },
        )

    response = make_auth_client(identity_engine).post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(identity.organization_id),
            "login_name": tab_login_name,
            "password": tab_password.get_secret_value(),
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(tab_user_id)
    with identity_engine.connect() as connection:
        assert connection.scalar(select(Session.organization_member_id)) == (tab_membership_id)


def test_unknown_login_still_runs_one_argon2_verification(
    identity_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_hashes: list[str] = []
    original_verify = login_service.verify_password

    def observe_verify(password: SecretStr, encoded_hash: str) -> bool:
        observed_hashes.append(encoded_hash)
        return original_verify(password, encoded_hash)

    monkeypatch.setattr(login_service, "verify_password", observe_verify)
    response = make_auth_client(identity_engine).post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(uuid4()),
            "login_name": f"unknown.{uuid4().hex}",
            "password": token_urlsafe(24),
        },
    )

    assert response.status_code == 401
    assert len(observed_hashes) == 1
    assert observed_hashes[0].startswith("$argon2id$")


@pytest.mark.parametrize(
    "failure_mode",
    [
        "unknown_login",
        "wrong_password",
        "wrong_organization",
        "inactive_organization",
        "inactive_user",
        "locked_user",
        "inactive_membership",
    ],
)
def test_all_credential_and_status_failures_have_the_same_safe_401(
    identity_engine: Engine,
    failure_mode: str,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    payload = _payload(identity)
    with identity_engine.begin() as connection:
        if failure_mode == "unknown_login":
            payload["login_name"] = f"unknown.{uuid4().hex}"
        elif failure_mode == "wrong_password":
            payload["password"] = token_urlsafe(24)
        elif failure_mode == "wrong_organization":
            payload["organization_id"] = str(uuid4())
        elif failure_mode == "inactive_organization":
            connection.execute(
                update(Organization)
                .where(Organization.id == identity.organization_id)
                .values(status="inactive")
            )
        elif failure_mode in {"inactive_user", "locked_user"}:
            connection.execute(
                update(User)
                .where(User.id == identity.user_id)
                .values(status="locked" if failure_mode == "locked_user" else "inactive")
            )
        elif failure_mode == "inactive_membership":
            connection.execute(
                update(OrganizationMember)
                .where(OrganizationMember.id == identity.membership_id)
                .values(status="inactive")
            )

    select_count = 0

    def count_selects(*args) -> None:
        nonlocal select_count
        statement = args[2]
        if statement.lstrip().upper().startswith("SELECT") and "FROM users" in statement:
            select_count += 1

    event.listen(identity_engine, "before_cursor_execute", count_selects)
    try:
        response = make_auth_client(identity_engine).post(
            "/api/v1/auth/login",
            json=payload,
        )
    finally:
        event.remove(identity_engine, "before_cursor_execute", count_selects)

    assert response.status_code == 401
    assert select_count == 1
    assert "www-authenticate" not in response.headers
    assert response.json() == {
        "error": {
            "code": "AUTHENTICATION_FAILED",
            "message": "登入資料不正確或帳號目前無法使用",
            "details": None,
        }
    }
    assert payload["password"] not in response.text
    with identity_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Session)) == 0
        assert (
            connection.scalar(select(User.last_login_at).where(User.id == identity.user_id)) is None
        )
