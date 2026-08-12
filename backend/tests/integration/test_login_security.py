"""PostgreSQL acceptance tests for login throttling and security evidence."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from secrets import token_urlsafe
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session as OrmSession

from app.modules.auth.errors import AuthenticationFailedError, LoginRateLimitedError
from app.modules.auth.models import LoginSecurityEvent, LoginThrottleState, Session
from app.modules.auth.services import create_login_session
from tests.integration.auth_test_support import create_auth_identity, make_auth_client
from tests.settings_factory import make_test_settings

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _payload(identity, password: str) -> dict[str, str]:
    return {
        "organization_id": str(identity.organization_id),
        "login_name": identity.login_name,
        "password": password,
    }


def test_fifth_failure_is_limited_without_storing_raw_identity(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    wrong_password = token_urlsafe(24)
    client = make_auth_client(identity_engine)

    responses = [
        client.post("/api/v1/auth/login", json=_payload(identity, wrong_password))
        for _ in range(6)
    ]

    assert [response.status_code for response in responses] == [
        401,
        401,
        401,
        401,
        429,
        429,
    ]
    assert int(responses[-1].headers["retry-after"]) > 0
    assert responses[-1].json()["error"]["code"] == "LOGIN_RATE_LIMITED"
    with identity_engine.connect() as connection:
        failure_count = connection.scalar(
            select(LoginThrottleState.failure_count)
        )
        events = connection.execute(
            select(
                LoginSecurityEvent.event_type,
                LoginSecurityEvent.credential_fingerprint,
                LoginSecurityEvent.request_id,
            ).order_by(LoginSecurityEvent.created_at)
        ).all()
        assert connection.scalar(select(func.count()).select_from(Session)) == 0

    assert failure_count == 5
    assert [event.event_type for event in events] == [
        "login_failed",
        "login_failed",
        "login_failed",
        "login_failed",
        "login_rate_limited",
        "login_rate_limited",
    ]
    persisted = " ".join(
        str(value)
        for event in events
        for value in (event.credential_fingerprint, event.request_id)
    )
    assert identity.login_name not in persisted
    assert wrong_password not in persisted
    assert {str(event.request_id) for event in events} == {
        response.headers["x-request-id"] for response in responses
    }


def test_success_clears_prior_failures_and_restarts_the_counter(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)
    wrong_password = token_urlsafe(24)

    for _ in range(2):
        assert client.post(
            "/api/v1/auth/login", json=_payload(identity, wrong_password)
        ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json=_payload(identity, identity.password.get_secret_value()),
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/login", json=_payload(identity, wrong_password)
    ).status_code == 401

    with identity_engine.connect() as connection:
        failure_count = connection.scalar(
            select(LoginThrottleState.failure_count)
        )
        prior_failure_count = connection.scalar(
            select(LoginSecurityEvent.failure_count).where(
                LoginSecurityEvent.event_type == "login_succeeded"
            )
        )

    assert failure_count == 1
    assert prior_failure_count == 2


def test_unknown_identity_uses_the_same_limit_and_public_response(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)
    payload = {
        "organization_id": str(identity.organization_id),
        "login_name": f"unknown.{uuid4().hex}",
        "password": token_urlsafe(24),
    }

    responses = [
        client.post("/api/v1/auth/login", json=payload) for _ in range(5)
    ]

    assert [response.status_code for response in responses] == [
        401,
        401,
        401,
        401,
        429,
    ]
    assert responses[-1].json()["error"]["code"] == "LOGIN_RATE_LIMITED"


def test_same_unknown_login_is_limited_independently_per_company(
    identity_engine: Engine,
) -> None:
    company_a = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    company_b = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)
    unknown_login = f"unknown.{uuid4().hex}"
    password = token_urlsafe(24)

    for _ in range(4):
        assert client.post(
            "/api/v1/auth/login",
            json={
                "organization_id": str(company_a.organization_id),
                "login_name": unknown_login,
                "password": password,
            },
        ).status_code == 401
    company_b_response = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(company_b.organization_id),
            "login_name": unknown_login,
            "password": password,
        },
    )
    company_a_response = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(company_a.organization_id),
            "login_name": unknown_login,
            "password": password,
        },
    )

    assert company_b_response.status_code == 401
    assert company_a_response.status_code == 429
    with identity_engine.connect() as connection:
        assert sorted(
            connection.scalars(select(LoginThrottleState.failure_count)).all()
        ) == [1, 5]


def test_concurrent_failures_do_not_lose_counts(identity_engine: Engine) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    wrong_password = SecretStr(token_urlsafe(24))
    barrier = Barrier(6)

    def attempt_login() -> int:
        barrier.wait()
        with OrmSession(identity_engine) as session:
            try:
                create_login_session(
                    session,
                    login_name=identity.login_name,
                    password=wrong_password,
                    organization_id=identity.organization_id,
                    request_id=uuid4(),
                    security_hmac_key=(
                        make_test_settings().auth_security_hmac_key_value()
                    ),
                )
            except AuthenticationFailedError:
                return 401
            except LoginRateLimitedError:
                return 429
        raise AssertionError("wrong password must not create a session")

    with ThreadPoolExecutor(max_workers=6) as executor:
        statuses = list(executor.map(lambda _: attempt_login(), range(6)))

    assert statuses.count(401) == 4
    assert statuses.count(429) == 2
    with identity_engine.connect() as connection:
        assert connection.scalar(
            select(LoginThrottleState.failure_count)
        ) == 5
        assert connection.scalar(
            select(func.count()).select_from(LoginSecurityEvent)
        ) == 6


def test_login_security_events_are_append_only(identity_engine: Engine) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    make_auth_client(identity_engine).post(
        "/api/v1/auth/login",
        json=_payload(identity, token_urlsafe(24)),
    )

    with pytest.raises(DBAPIError):
        with identity_engine.begin() as connection:
            connection.execute(
                update(LoginSecurityEvent).values(failure_count=999)
            )
