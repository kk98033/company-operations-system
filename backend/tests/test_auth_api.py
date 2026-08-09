"""Focused HTTP contract tests for auth endpoints without a real database."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app
from app.modules.auth import api as auth_api
from app.modules.auth.errors import AuthenticationFailedError, SessionCreationError
from app.modules.auth.services.login import LoginResult
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings


@pytest.fixture
def auth_client() -> TestClient:
    session_factory = Mock(return_value=Mock())
    return TestClient(
        create_app(
            settings=make_test_settings(),
            database_resources=make_database_resources(
                session_factory=session_factory,
            ),
            readiness_checks=[],
        )
    )


def _login_payload(password: str) -> dict[str, str]:
    return {
        "organization_id": str(uuid4()),
        "login_name": "test.operator",
        "password": password,
    }


def test_login_returns_raw_token_once_with_no_store_headers(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = token_urlsafe(24)
    raw_token = token_urlsafe(32)
    now = datetime.now(UTC)
    user_id = uuid4()
    organization_id = uuid4()

    def fake_login(*args, **kwargs) -> LoginResult:
        assert isinstance(kwargs["password"], SecretStr)
        assert kwargs["password"].get_secret_value() == password
        return LoginResult(
            raw_session_token=SecretStr(raw_token),
            expires_at=now + timedelta(hours=8),
            user_id=user_id,
            login_name="test.operator",
            display_name="Synthetic Operator",
            organization_id=organization_id,
            organization_name="Synthetic Organization",
        )

    monkeypatch.setattr(auth_api, "create_login_session", fake_login)
    response = auth_client.post("/api/v1/auth/login", json=_login_payload(password))

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.json()["session_token"] == raw_token
    assert response.json()["token_type"] == "Bearer"
    assert response.json()["user"]["id"] == str(user_id)
    assert response.json()["organization"]["id"] == str(organization_id)
    assert password not in response.text


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (AuthenticationFailedError(), 401, "AUTHENTICATION_FAILED"),
        (SessionCreationError(), 500, "SESSION_CREATION_FAILED"),
    ],
)
def test_login_domain_errors_use_safe_fixed_responses(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    password = token_urlsafe(24)

    def fail_login(*args, **kwargs):
        raise error

    monkeypatch.setattr(auth_api, "create_login_session", fail_login)
    response = auth_client.post("/api/v1/auth/login", json=_login_payload(password))

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.json()["error"]["details"] is None
    assert password not in response.text
    if expected_status == 401:
        assert response.headers["www-authenticate"] == 'Bearer realm="company-system"'
    else:
        assert "www-authenticate" not in response.headers


def test_login_validation_never_echoes_password(
    auth_client: TestClient,
) -> None:
    password = "x" * 257
    response = auth_client.post("/api/v1/auth/login", json=_login_payload(password))

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert password not in response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_logout_is_idempotent_at_the_http_boundary(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_token = token_urlsafe(32)
    observed_tokens: list[str] = []

    def fake_revoke(*args, **kwargs) -> None:
        observed_tokens.append(kwargs["raw_token"].get_secret_value())

    monkeypatch.setattr(auth_api, "revoke_session", fake_revoke)
    headers = {"Authorization": f"Bearer {raw_token}"}

    first = auth_client.post("/api/v1/auth/logout", headers=headers)
    second = auth_client.post("/api/v1/auth/logout", headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204
    assert first.content == b""
    assert second.content == b""
    assert observed_tokens == [raw_token, raw_token]


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic abc", "Bearer short", "Bearer " + "A" * 42 + "="],
)
def test_logout_rejects_missing_or_malformed_bearer_without_echoing_it(
    auth_client: TestClient,
    authorization: str | None,
) -> None:
    headers = {} if authorization is None else {"Authorization": authorization}
    response = auth_client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Bearer realm="company-system"'
    assert response.json()["error"]["code"] == "SESSION_INVALID"
    if authorization:
        assert authorization not in response.text
