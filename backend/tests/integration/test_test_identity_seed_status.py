"""Status conflict checks for the synthetic identity seed."""

from __future__ import annotations

import os
from secrets import token_urlsafe

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.orm import Session as OrmSession

from app.core.config import AppEnvironment
from app.modules.auth.models import User
from app.modules.organizations.models import Organization, OrganizationMember
from app.seeds.test_identity import (
    TEST_ADMIN_MEMBER_ID,
    TEST_ADMIN_USER_ID,
    TEST_ORGANIZATION_ID,
    SeedConflictError,
    seed_test_identity,
)

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


@pytest.mark.parametrize(
    ("model", "row_id"),
    [
        (Organization, TEST_ORGANIZATION_ID),
        (User, TEST_ADMIN_USER_ID),
        (OrganizationMember, TEST_ADMIN_MEMBER_ID),
    ],
)
def test_seed_rejects_inactive_existing_identity_without_reactivating_it(
    identity_engine: Engine,
    model: type[Organization] | type[User] | type[OrganizationMember],
    row_id: object,
) -> None:
    admin_password = SecretStr(token_urlsafe(24))
    operator_password = SecretStr(token_urlsafe(24))
    with OrmSession(identity_engine) as session:
        seed_test_identity(
            session,
            environment=AppEnvironment.TEST,
            admin_password=admin_password,
            operator_password=operator_password,
        )
        with session.begin():
            row = session.get(model, row_id)
            assert row is not None
            row.status = "inactive"

    with OrmSession(identity_engine) as session:
        with pytest.raises(SeedConflictError):
            seed_test_identity(
                session,
                environment=AppEnvironment.TEST,
                admin_password=admin_password,
                operator_password=operator_password,
            )

    with OrmSession(identity_engine) as session:
        row = session.get(model, row_id)
        assert row is not None
        assert row.status == "inactive"
