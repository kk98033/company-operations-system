"""PostgreSQL-backed acceptance test for restoring a browser Session."""

from __future__ import annotations

import os
from secrets import token_urlsafe

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine

from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def test_browser_cookie_loads_current_session_without_exposing_credentials(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    client = make_auth_client(identity_engine)
    login = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(identity.organization_id),
            "login_name": identity.login_name,
            "password": identity.password.get_secret_value(),
        },
    )

    current = client.get("/api/v1/auth/session")

    assert login.status_code == 200
    assert current.status_code == 200
    assert current.headers["cache-control"] == "no-store"
    assert current.headers["pragma"] == "no-cache"
    assert current.json() == login.json()
    assert "session_token" not in current.json()
    assert "token_type" not in current.json()
