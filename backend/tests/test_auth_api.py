"""Focused HTTP contract tests for browser authentication endpoints."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app
from app.modules.auth import api as auth_api
from app.modules.auth.cookies import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from app.modules.auth.csrf import derive_csrf_token
from app.modules.auth.errors import AuthenticationFailedError, SessionCreationError
from app.modules.auth.services.login import LoginResult
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings

TRUSTED_ORIGIN = "http://testserver"


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


def _trusted_headers(**extra: str) -> dict[str, str]:
    return {"Origin": TRUSTED_ORIGIN, **extra}


def _login_result(raw_token: str) -> LoginResult:
    now = datetime.now(UTC)
    return LoginResult(
        raw_session_token=SecretStr(raw_token),
        expires_at=now + timedelta(hours=8),
        user_id=uuid4(),
        login_name="test.operator",
        display_name="Synthetic Operator",
        organization_id=uuid4(),
        organization_name="Synthetic Organization",
    )


def _csrf_for(client: TestClient, raw_token: SecretStr) -> str:
    return derive_csrf_token(
        raw_token,
        signing_key=client.app.state.settings.csrf_hmac_key_value(),
    ).get_secret_value()


def test_login_sets_browser_session_cookies_without_returning_raw_token(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = token_urlsafe(24)
    raw_token = token_urlsafe(32)

    def fake_login(*args, **kwargs) -> LoginResult:
        assert isinstance(kwargs["password"], SecretStr)
        assert kwargs["password"].get_secret_value() == password
        return _login_result(raw_token)

    monkeypatch.setattr(auth_api, "create_login_session", fake_login)
    response = auth_client.post(
        "/api/v1/auth/login",
        json=_login_payload(password),
        headers=_trusted_headers(),
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert "session_token" not in response.json()
    assert "token_type" not in response.json()
    assert response.cookies[SESSION_COOKIE_NAME] == raw_token
    expected_csrf = _csrf_for(auth_client, SecretStr(raw_token))
    assert response.cookies[CSRF_COOKIE_NAME] == expected_csrf

    cookie_headers = response.headers.get_list("set-cookie")
    session_header = next(
        value for value in cookie_headers if value.startswith(SESSION_COOKIE_NAME)
    )
    csrf_header = next(
        value for value in cookie_headers if value.startswith(CSRF_COOKIE_NAME)
    )
    assert "HttpOnly" in session_header
    assert "Path=/api/v1" in session_header
    assert "HttpOnly" not in csrf_header
    assert "Path=/" in csrf_header
    for value in cookie_headers:
        assert "SameSite=strict" in value
        assert "Secure" not in value
        assert "Domain=" not in value
        assert "Max-Age=" not in value
        assert "Expires=" not in value
    assert raw_token not in response.text
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
    response = auth_client.post(
        "/api/v1/auth/login",
        json=_login_payload(password),
        headers=_trusted_headers(),
    )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["details"] is None
    assert password not in response.text
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({}, 403),
        ({"Origin": "null"}, 403),
        ({"Origin": "https://evil.example"}, 403),
        ({"Origin": "http://testserver.evil"}, 403),
        ({"Referer": "http://testserver/login"}, 200),
    ],
)
def test_login_requires_exact_origin_or_referer_before_credentials(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    login = Mock(return_value=_login_result(token_urlsafe(32)))
    monkeypatch.setattr(auth_api, "create_login_session", login)

    response = auth_client.post(
        "/api/v1/auth/login",
        json=_login_payload(token_urlsafe(24)),
        headers=headers,
    )

    assert response.status_code == expected_status
    assert login.call_count == (1 if expected_status == 200 else 0)
    if expected_status == 403:
        assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"
        assert "set-cookie" not in response.headers


def test_login_rejects_duplicate_or_conflicting_source_headers(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    login = Mock(return_value=_login_result(token_urlsafe(32)))
    monkeypatch.setattr(auth_api, "create_login_session", login)
    payload = _login_payload(token_urlsafe(24))

    duplicate = auth_client.post(
        "/api/v1/auth/login",
        json=payload,
        headers=[
            ("Origin", TRUSTED_ORIGIN),
            ("Origin", TRUSTED_ORIGIN),
        ],
    )
    conflict = auth_client.post(
        "/api/v1/auth/login",
        json=payload,
        headers={
            "Origin": TRUSTED_ORIGIN,
            "Referer": "https://evil.example/login",
        },
    )

    assert duplicate.status_code == 403
    assert conflict.status_code == 403
    login.assert_not_called()


def test_login_validation_never_echoes_password(auth_client: TestClient) -> None:
    password = "x" * 257
    response = auth_client.post(
        "/api/v1/auth/login",
        json=_login_payload(password),
        headers=_trusted_headers(),
    )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert password not in response.text
