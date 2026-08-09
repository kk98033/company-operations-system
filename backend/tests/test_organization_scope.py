"""Organization scope dependency and application contract tests."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.modules.auth.dependencies import require_current_session
from app.modules.auth.services import AuthenticatedSession
from app.modules.organizations.dependencies import require_organization_scope
from app.modules.organizations.scope import (
    CrossOrganizationReferenceError,
    OrganizationScope,
    OrganizationScopeContractError,
)
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
    )


def test_scope_dependency_ignores_untrusted_request_company_values() -> None:
    context = _context()
    other_organization_id = uuid4()
    app = create_app(
        settings=make_test_settings(),
        database_resources=make_database_resources(session_factory=Mock()),
        readiness_checks=[],
    )
    app.dependency_overrides[require_current_session] = lambda: context

    @app.post("/_test/scoped")
    def scoped_probe(
        scope: Annotated[
            OrganizationScope,
            Depends(require_organization_scope),
        ],
    ) -> dict[str, str]:
        return {"organization_id": str(scope.organization_id)}

    response = TestClient(app).post(
        f"/_test/scoped?organization_id={other_organization_id}",
        headers={"X-Organization-ID": str(other_organization_id)},
        json={"organization_id": str(other_organization_id)},
    )

    assert response.status_code == 200
    assert response.json() == {"organization_id": str(context.organization_id)}


def test_scope_injects_create_ownership_and_rejects_caller_override() -> None:
    scope = OrganizationScope(uuid4(), uuid4(), uuid4())

    assert scope.create_values({"code": "synthetic"}) == {
        "code": "synthetic",
        "organization_id": scope.organization_id,
    }
    with pytest.raises(OrganizationScopeContractError, match="authenticated scope"):
        scope.create_values({"organization_id": uuid4(), "code": "forged"})


def test_scope_rejects_model_without_organization_contract() -> None:
    scope = OrganizationScope(uuid4(), uuid4(), uuid4())

    with pytest.raises(OrganizationScopeContractError, match="organization_id"):
        scope.constrain(select(1), model=object)


def test_scope_rejects_cross_company_reference_without_exposing_ids() -> None:
    scope = OrganizationScope(uuid4(), uuid4(), uuid4())
    other_organization_id = uuid4()

    scope.require_same_organization(scope.organization_id)
    with pytest.raises(CrossOrganizationReferenceError) as error:
        scope.require_same_organization(other_organization_id)

    assert str(scope.organization_id) not in str(error.value)
    assert str(other_organization_id) not in str(error.value)
