"""PostgreSQL acceptance tests for organization-scoped RBAC."""

from __future__ import annotations

import os
from secrets import token_urlsafe
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.modules.authorization import has_capability, list_capabilities
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from tests.integration.auth_test_support import create_auth_identity, make_auth_client
from tests.integration.identity_test_support import seed_identity

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _grant(
    engine: Engine,
    *,
    organization_id,
    membership_id,
    role_code: str,
    permission_code: str,
) -> tuple[UUID, UUID]:
    role = Role(
        id=uuid4(),
        organization_id=organization_id,
        code=role_code,
        name=f"Synthetic {role_code}",
    )
    permission = Permission(
        id=uuid4(),
        code=permission_code,
        name=f"Synthetic {permission_code}",
    )
    role_id = role.id
    permission_id = permission.id
    with OrmSession(engine) as session, session.begin():
        session.add_all([role, permission])
        session.flush()
        session.add_all(
            [
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                ),
                OrganizationMemberRole(
                    organization_id=organization_id,
                    organization_member_id=membership_id,
                    role_id=role.id,
                ),
            ]
        )
    return role_id, permission_id


def test_active_grant_is_exact_sorted_and_inactive_rows_deny(
    identity_engine: Engine,
) -> None:
    organization_id, _, member_id, _ = seed_identity(identity_engine)
    role_id, permission_id = _grant(
        identity_engine,
        organization_id=organization_id,
        membership_id=member_id,
        role_code="operator",
        permission_code="work_order.read",
    )
    second_permission = Permission(
        id=uuid4(), code="case.read", name="Synthetic Case Read"
    )
    with OrmSession(identity_engine) as session, session.begin():
        session.add(second_permission)
        session.flush()
        session.add(
            RolePermission(
                role_id=role_id,
                permission_id=second_permission.id,
            )
        )

    with OrmSession(identity_engine) as session:
        assert list_capabilities(
            session,
            organization_member_id=member_id,
            organization_id=organization_id,
        ) == ("case.read", "work_order.read")
        assert has_capability(
            session,
            organization_member_id=member_id,
            organization_id=organization_id,
            capability="work_order.read",
        )
        assert not has_capability(
            session,
            organization_member_id=member_id,
            organization_id=organization_id,
            capability="work_order.write",
        )

    with OrmSession(identity_engine) as session, session.begin():
        session.get(Permission, permission_id).status = "inactive"
    with OrmSession(identity_engine) as session:
        assert not has_capability(
            session,
            organization_member_id=member_id,
            organization_id=organization_id,
            capability="work_order.read",
        )

    with OrmSession(identity_engine) as session, session.begin():
        session.get(Permission, permission_id).status = "active"
        session.get(Role, role_id).status = "inactive"
    with OrmSession(identity_engine) as session:
        assert not has_capability(
            session,
            organization_member_id=member_id,
            organization_id=organization_id,
            capability="work_order.read",
        )


def test_database_rejects_cross_organization_role_assignment(
    identity_engine: Engine,
) -> None:
    first_org_id, _, first_member_id, _ = seed_identity(identity_engine)
    second_org_id, _, second_member_id, _ = seed_identity(identity_engine)
    role_id, _ = _grant(
        identity_engine,
        organization_id=first_org_id,
        membership_id=first_member_id,
        role_code="operator",
        permission_code="work_order.read",
    )

    with OrmSession(identity_engine) as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(
                    OrganizationMemberRole(
                        organization_id=second_org_id,
                        organization_member_id=second_member_id,
                        role_id=role_id,
                    )
                )


def test_login_and_current_session_expose_only_active_company_capabilities(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(token_urlsafe(24)),
    )
    _grant(
        identity_engine,
        organization_id=identity.organization_id,
        membership_id=identity.membership_id,
        role_code="access_manager",
        permission_code="settings.manage",
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
    assert login.json()["capabilities"] == ["settings.manage"]
    assert current.json()["capabilities"] == ["settings.manage"]


@pytest.mark.parametrize(
    ("permission_code", "role_code"),
    [
        ("Work_Order.Read", "operator"),
        ("work_order", "operator"),
        ("work_order.read", "Operator"),
        ("work_order.read", "operator.admin"),
    ],
)
def test_database_rejects_noncanonical_codes(
    identity_engine: Engine,
    permission_code: str,
    role_code: str,
) -> None:
    organization_id, _, _, _ = seed_identity(identity_engine)
    with OrmSession(identity_engine) as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add_all(
                    [
                        Permission(
                            id=uuid4(),
                            code=permission_code,
                            name="Synthetic Permission",
                        ),
                        Role(
                            id=uuid4(),
                            organization_id=organization_id,
                            code=role_code,
                            name="Synthetic Role",
                        ),
                    ]
                )
