"""Deny-by-default contract for reusable capability dependencies."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.database.session import get_database_session
from app.main import create_app
from app.modules.auth.dependencies import require_current_session
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization import dependencies as authorization_dependencies
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings


def _context() -> AuthenticatedSession:
    return AuthenticatedSession(
        expires_at=datetime.now(UTC) + timedelta(hours=8),
        organization_member_id=uuid4(),
        user_id=uuid4(),
        login_name="synthetic.operator",
        display_name="Synthetic Operator",
        organization_id=uuid4(),
        organization_name="Synthetic Organization",
        session_id=uuid4(),
    )


@pytest.mark.parametrize(
    ("allowed", "expected_status", "expected_code"),
    [(True, 200, None), (False, 403, "PERMISSION_DENIED")],
)
def test_capability_dependency_allows_exact_grant_and_denies_missing_grant(
    monkeypatch: pytest.MonkeyPatch,
    allowed: bool,
    expected_status: int,
    expected_code: str | None,
) -> None:
    context = _context()
    database_session = Mock()
    checker = Mock(return_value=allowed)
    monkeypatch.setattr(authorization_dependencies, "has_capability", checker)
    app = create_app(
        settings=make_test_settings(),
        database_resources=make_database_resources(session_factory=Mock()),
        readiness_checks=[],
    )
    app.dependency_overrides[require_current_session] = lambda: context
    app.dependency_overrides[get_database_session] = lambda: database_session
    guard = authorization_dependencies.require_capability("settings.manage")

    @app.get("/_test/settings")
    def settings_probe(
        current: Annotated[AuthenticatedSession, Depends(guard)],
    ) -> dict[str, str]:
        return {"organization_id": str(current.organization_id)}

    response = TestClient(app).get("/_test/settings")

    assert response.status_code == expected_status
    if expected_code is not None:
        assert response.json()["error"]["code"] == expected_code
        database_session.add.assert_called_once()
        database_session.commit.assert_called_once_with()
    else:
        database_session.add.assert_not_called()
    checker.assert_called_once_with(
        database_session,
        organization_member_id=context.organization_member_id,
        organization_id=context.organization_id,
        capability="settings.manage",
    )


@pytest.mark.parametrize(
    "code",
    ["admin", "Settings.Manage", " settings.manage", "settings.*", "a..read"],
)
def test_capability_dependency_rejects_invalid_developer_configuration(
    code: str,
) -> None:
    with pytest.raises(ValueError, match="capability code"):
        authorization_dependencies.require_capability(code)
