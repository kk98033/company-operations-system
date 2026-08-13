"""PostgreSQL A/B company read and write isolation tests."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session as OrmSession

from app.modules.authorization.models import Role
from app.modules.organizations.scope import (
    OrganizationScope,
    OrganizationScopeContractError,
)
from tests.integration.identity_test_support import seed_identity

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _scope(
    organization_id: UUID,
    member_id: UUID,
    user_id: UUID,
) -> OrganizationScope:
    return OrganizationScope(
        organization_id=organization_id,
        organization_member_id=member_id,
        actor_user_id=user_id,
    )


def _seed_roles(
    engine: Engine,
) -> tuple[OrganizationScope, UUID, UUID, UUID]:
    org_a, user_a, member_a, _ = seed_identity(engine)
    org_b, _, _, _ = seed_identity(engine)
    role_a = Role(id=uuid4(), organization_id=org_a, code="operator", name="A Operator")
    role_b = Role(id=uuid4(), organization_id=org_b, code="operator", name="B Operator")
    role_a_id, role_b_id = role_a.id, role_b.id
    with OrmSession(engine) as session, session.begin():
        session.add_all([role_a, role_b])
    return _scope(org_a, member_a, user_a), role_a_id, role_b_id, org_b


def test_company_a_scoped_select_cannot_observe_company_b_row(
    identity_engine: Engine,
) -> None:
    scope_a, role_a_id, role_b_id, _ = _seed_roles(identity_engine)

    with OrmSession(identity_engine) as session:
        own_statement = scope_a.constrain(
            select(Role).where(Role.id == role_a_id),
            model=Role,
        )
        foreign_statement = scope_a.constrain(
            select(Role).where(Role.id == role_b_id),
            model=Role,
        )
        assert session.scalar(own_statement).id == role_a_id
        assert session.scalar(foreign_statement) is None


def test_company_a_scoped_update_cannot_modify_company_b_row(
    identity_engine: Engine,
) -> None:
    scope_a, role_a_id, role_b_id, _ = _seed_roles(identity_engine)

    with OrmSession(identity_engine) as session, session.begin():
        foreign_update = scope_a.constrain(
            update(Role).where(Role.id == role_b_id).values(name="Forged"),
            model=Role,
        )
        own_update = scope_a.constrain(
            update(Role).where(Role.id == role_a_id).values(name="Updated A"),
            model=Role,
        )
        assert session.execute(foreign_update).rowcount == 0
        assert session.execute(own_update).rowcount == 1

    with OrmSession(identity_engine) as session:
        assert session.get(Role, role_a_id).name == "Updated A"
        assert session.get(Role, role_b_id).name == "B Operator"


def test_create_ownership_is_injected_and_override_fails_before_write(
    identity_engine: Engine,
) -> None:
    scope_a, _, _, organization_b_id = _seed_roles(identity_engine)
    role_id = uuid4()

    with OrmSession(identity_engine) as session, session.begin():
        session.add(
            Role(
                id=role_id,
                **scope_a.create_values({"code": "reader", "name": "A Reader"}),
            )
        )

    with pytest.raises(OrganizationScopeContractError):
        scope_a.create_values(
            {
                "organization_id": organization_b_id,
                "code": "forged",
                "name": "Forged",
            }
        )
    with OrmSession(identity_engine) as session:
        created = session.get(Role, role_id)
        assert created.organization_id == scope_a.organization_id
        assert session.scalar(select(Role).where(Role.code == "forged")) is None
