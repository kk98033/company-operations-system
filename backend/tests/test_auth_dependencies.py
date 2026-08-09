"""HTTP probes for the reusable Cookie-only current Session dependency."""

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.auth import dependencies as auth_dependencies
from app.modules.auth.cookies import SESSION_COOKIE_NAME
from app.modules.auth.services import AuthenticatedSession
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings


@pytest.fixture
def dependency_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    context = AuthenticatedSession(
        expires_at=datetime.now(UTC) + timedelta(hours=8),
        user_id=uuid4(),
        login_name="synthetic.operator",
        display_name="Synthetic Operator",
        organization_id=uuid4(),
        organization_name="Synthetic Organization",
    )
    monkeypatch.setattr(auth_dependencies, "get_active_session", Mock(return_value=context))
    app = create_app(
        settings=make_test_settings(),
        database_resources=make_database_resources(session_factory=Mock(return_value=Mock())),
        readiness_checks=[],
    )

    @app.get("/_test/current-session")
    def current_session_probe(
        current: Annotated[
            AuthenticatedSession,
            Depends(auth_dependencies.require_current_session),
        ],
    ) -> dict[str, str]:
        return {
            "user_id": str(current.user_id),
            "organization_id": str(current.organization_id),
        }

    return TestClient(app)


def test_current_session_dependency_accepts_only_session_cookie(
    dependency_client: TestClient,
) -> None:
    raw_token = token_urlsafe(32)
    dependency_client.cookies.set(SESSION_COOKIE_NAME, raw_token)
    accepted = dependency_client.get("/_test/current-session")
    dependency_client.cookies.clear()
    bearer_only = dependency_client.get(
        "/_test/current-session",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    dependency_client.cookies.set(SESSION_COOKIE_NAME, "malformed")
    malformed = dependency_client.get("/_test/current-session")

    assert accepted.status_code == 200
    for response in (bearer_only, malformed):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "SESSION_INVALID"


@pytest.mark.parametrize("valid_first", [True, False])
def test_current_session_dependency_rejects_duplicate_session_cookies(
    dependency_client: TestClient,
    valid_first: bool,
) -> None:
    valid = token_urlsafe(32)
    malformed = "malformed"
    ordered = (valid, malformed) if valid_first else (malformed, valid)

    response = dependency_client.get(
        "/_test/current-session",
        headers={
            "Cookie": "; ".join(
                f"{SESSION_COOKIE_NAME}={value}" for value in ordered
            )
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"


def test_production_current_session_endpoint_uses_cookie_dependency(
    dependency_client: TestClient,
) -> None:
    raw_token = token_urlsafe(32)
    dependency_client.cookies.set(
        SESSION_COOKIE_NAME,
        raw_token,
        path="/api/v1",
    )

    response = dependency_client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["user"]["login_name"] == "synthetic.operator"
