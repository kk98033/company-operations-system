"""Browser logout and production Cookie policy contracts."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import AppSettings
from app.main import create_app
from app.modules.auth import api as auth_api
from app.modules.auth.cookies import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from app.modules.auth.csrf import derive_csrf_token
from app.modules.auth.services.login import LoginResult
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings, valid_settings_values


@pytest.fixture
def auth_client() -> TestClient:
    return TestClient(
        create_app(
            settings=make_test_settings(),
            database_resources=make_database_resources(session_factory=Mock(return_value=Mock())),
            readiness_checks=[],
        ),
        raise_server_exceptions=False,
    )


def _csrf_for(client: TestClient, raw_token: SecretStr) -> str:
    return derive_csrf_token(
        raw_token,
        signing_key=client.app.state.settings.csrf_hmac_key_value(),
    ).get_secret_value()


def _browser_request(
    client: TestClient,
    raw_token: SecretStr,
    csrf_token: str,
) -> dict[str, dict[str, str]]:
    client.cookies.set(
        SESSION_COOKIE_NAME,
        raw_token.get_secret_value(),
        path="/api/v1",
    )
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token, path="/")
    return {
        "headers": {
            "Origin": "http://testserver",
            "X-CSRF-Token": csrf_token,
        }
    }


def test_logout_revokes_then_clears_both_cookie_paths(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_token = SecretStr(token_urlsafe(32))
    csrf_token = _csrf_for(auth_client, raw_token)
    revoke = Mock()
    monkeypatch.setattr(auth_api, "revoke_session", revoke)

    response = auth_client.post(
        "/api/v1/auth/logout",
        **_browser_request(auth_client, raw_token, csrf_token),
    )

    assert response.status_code == 204
    assert revoke.call_args.kwargs["raw_token"].get_secret_value() == (raw_token.get_secret_value())
    deleted = response.headers.get_list("set-cookie")
    session_header = next(value for value in deleted if value.startswith(SESSION_COOKIE_NAME))
    csrf_header = next(value for value in deleted if value.startswith(CSRF_COOKIE_NAME))
    assert "Path=/api/v1" in session_header
    assert "Path=/" in csrf_header
    assert all("Max-Age=0" in value for value in deleted)
    assert all("SameSite=strict" in value for value in deleted)


@pytest.mark.parametrize("raw_cookie", [None, "malformed"])
def test_logout_without_usable_session_is_idempotent_and_clears_cookies(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    raw_cookie: str | None,
) -> None:
    revoke = Mock()
    monkeypatch.setattr(auth_api, "revoke_session", revoke)
    if raw_cookie is not None:
        auth_client.cookies.set(SESSION_COOKIE_NAME, raw_cookie, path="/api/v1")
    response = auth_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 204
    revoke.assert_not_called()
    assert len(response.headers.get_list("set-cookie")) == 2


@pytest.mark.parametrize("failure", ["origin", "header", "cookie", "forged"])
def test_logout_rejects_origin_or_csrf_without_revoking_or_clearing(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    raw_token = SecretStr(token_urlsafe(32))
    csrf_token = _csrf_for(auth_client, raw_token)
    request = _browser_request(auth_client, raw_token, csrf_token)
    if failure == "origin":
        request["headers"]["Origin"] = "https://evil.example"
    elif failure == "header":
        request["headers"].pop("X-CSRF-Token")
    elif failure == "cookie":
        auth_client.cookies.delete(CSRF_COOKIE_NAME, path="/")
    else:
        forged = "A" * 43
        auth_client.cookies.set(CSRF_COOKIE_NAME, forged, path="/")
        request["headers"]["X-CSRF-Token"] = forged
    revoke = Mock()
    monkeypatch.setattr(auth_api, "revoke_session", revoke)

    response = auth_client.post("/api/v1/auth/logout", **request)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"
    revoke.assert_not_called()
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("valid_first", [True, False])
@pytest.mark.parametrize("duplicate", ["header", "cookie"])
def test_logout_rejects_duplicate_security_values_in_every_order(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    duplicate: str,
    valid_first: bool,
) -> None:
    raw_token = SecretStr(token_urlsafe(32))
    valid = _csrf_for(auth_client, raw_token)
    forged = "A" * 43
    ordered = (valid, forged) if valid_first else (forged, valid)
    cookie_parts = [
        f"{SESSION_COOKIE_NAME}={raw_token.get_secret_value()}",
    ]
    headers: list[tuple[str, str]] = [("Origin", "http://testserver")]
    if duplicate == "header":
        cookie_parts.append(f"{CSRF_COOKIE_NAME}={valid}")
        headers.extend(("X-CSRF-Token", value) for value in ordered)
    else:
        cookie_parts.extend(f"{CSRF_COOKIE_NAME}={value}" for value in ordered)
        headers.append(("X-CSRF-Token", valid))
    headers.append(("Cookie", "; ".join(cookie_parts)))
    revoke = Mock()
    monkeypatch.setattr(auth_api, "revoke_session", revoke)

    response = auth_client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"
    revoke.assert_not_called()
    assert "set-cookie" not in response.headers


def test_logout_database_failure_does_not_clear_browser_credentials(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_token = SecretStr(token_urlsafe(32))
    csrf_token = _csrf_for(auth_client, raw_token)
    monkeypatch.setattr(
        auth_api,
        "revoke_session",
        Mock(side_effect=RuntimeError("database-canary")),
    )
    response = auth_client.post(
        "/api/v1/auth/logout",
        **_browser_request(auth_client, raw_token, csrf_token),
    )

    assert response.status_code == 500
    assert "set-cookie" not in response.headers
    assert "database-canary" not in response.text


def test_production_login_cookies_are_always_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_api, "list_capabilities", Mock(return_value=()))
    settings = AppSettings.model_validate(
        valid_settings_values(
            APP_ENV="production",
            DATABASE_URL=(
                "postgresql+psycopg://company_system_prod:production-only"
                "@database.internal/company_system_prod"
            ),
        )
    )
    client = TestClient(
        create_app(
            settings=settings,
            database_resources=make_database_resources(session_factory=Mock(return_value=Mock())),
            readiness_checks=[],
        )
    )
    monkeypatch.setattr(
        auth_api,
        "create_login_session",
        Mock(
            return_value=LoginResult(
                raw_session_token=SecretStr(token_urlsafe(32)),
                expires_at=datetime.now(UTC) + timedelta(hours=8),
                organization_member_id=uuid4(),
                user_id=uuid4(),
                login_name="test.operator",
                display_name="Synthetic Operator",
                organization_id=uuid4(),
                organization_name="Synthetic Organization",
            )
        ),
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(uuid4()),
            "login_name": "test.operator",
            "password": token_urlsafe(24),
        },
        headers={"Origin": "https://company.example"},
    )

    assert response.status_code == 200
    assert all("Secure" in header for header in response.headers.get_list("set-cookie"))
