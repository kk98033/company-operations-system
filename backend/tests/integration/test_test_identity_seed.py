"""PostgreSQL acceptance tests for the development/test identity seed."""

from __future__ import annotations

import os
from secrets import token_urlsafe

import pytest
from argon2 import PasswordHasher
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session as OrmSession

from app.core.config import AppEnvironment
from app.modules.auth.models import Session, User
from app.modules.auth.passwords import hash_password
from app.modules.organizations.models import Organization, OrganizationMember
from app.seeds.test_identity import (
    TEST_ADMIN_DISPLAY_NAME,
    TEST_ADMIN_LOGIN_NAME,
    TEST_ADMIN_USER_ID,
    TEST_OPERATOR_DISPLAY_NAME,
    TEST_OPERATOR_LOGIN_NAME,
    TEST_OPERATOR_USER_ID,
    TEST_ORGANIZATION_ID,
    TEST_ORGANIZATION_NAME,
    SeedConflictError,
    SeedSafetyError,
    seed_test_identity,
)

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


@pytest.fixture
def seed_passwords() -> tuple[SecretStr, SecretStr]:
    return SecretStr(token_urlsafe(24)), SecretStr(token_urlsafe(24))


def _run_seed(
    engine: Engine,
    *,
    admin_password: SecretStr,
    operator_password: SecretStr,
    environment: AppEnvironment = AppEnvironment.TEST,
):
    with OrmSession(engine) as session:
        return seed_test_identity(
            session,
            environment=environment,
            admin_password=admin_password,
            operator_password=operator_password,
        )


def test_seed_creates_only_synthetic_company_users_and_memberships(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    admin_password, operator_password = seed_passwords
    result = _run_seed(
        identity_engine,
        admin_password=admin_password,
        operator_password=operator_password,
    )

    assert result.created_organizations == 1
    assert result.created_users == 2
    assert result.created_memberships == 2
    with OrmSession(identity_engine) as session:
        organization = session.get(Organization, TEST_ORGANIZATION_ID)
        users = session.scalars(
            select(User).where(User.id.in_([TEST_ADMIN_USER_ID, TEST_OPERATOR_USER_ID]))
        ).all()
        membership_count = session.scalar(
            select(func.count()).select_from(OrganizationMember)
        )
        session_count = session.scalar(select(func.count()).select_from(Session))

    assert organization is not None
    assert organization.name == "測試印刷股份有限公司（虛構）"
    assert {user.login_name for user in users} == {
        TEST_ADMIN_LOGIN_NAME,
        TEST_OPERATOR_LOGIN_NAME,
    }
    assert membership_count == 2
    assert session_count == 0
    assert len({user.password_hash for user in users}) == 2
    passwords_by_login = {
        TEST_ADMIN_LOGIN_NAME: admin_password,
        TEST_OPERATOR_LOGIN_NAME: operator_password,
    }
    for user in users:
        assert user.password_hash.startswith("$argon2id$")
        password = passwords_by_login[user.login_name]
        assert password.get_secret_value() not in user.password_hash
        assert PasswordHasher().verify(
            user.password_hash, password.get_secret_value()
        )


def test_seed_is_idempotent_and_keeps_existing_hashes(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    admin_password, operator_password = seed_passwords
    first_result = _run_seed(
        identity_engine,
        admin_password=admin_password,
        operator_password=operator_password,
    )
    with OrmSession(identity_engine) as session:
        first_hashes = dict(session.execute(select(User.id, User.password_hash)).all())

    second_result = _run_seed(
        identity_engine,
        admin_password=admin_password,
        operator_password=operator_password,
    )
    with OrmSession(identity_engine) as session:
        second_hashes = dict(session.execute(select(User.id, User.password_hash)).all())
        counts = (
            session.scalar(select(func.count()).select_from(Organization)),
            session.scalar(select(func.count()).select_from(User)),
            session.scalar(select(func.count()).select_from(OrganizationMember)),
        )

    assert first_result.created_users == 2
    assert second_result.created_organizations == 0
    assert second_result.created_users == 0
    assert second_result.created_memberships == 0
    assert second_hashes == first_hashes
    assert counts == (1, 2, 2)


def test_seed_rejects_changed_password_without_rotating_existing_hash(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    admin_password, operator_password = seed_passwords
    _run_seed(
        identity_engine,
        admin_password=admin_password,
        operator_password=operator_password,
    )
    with OrmSession(identity_engine) as session:
        original_hashes = dict(session.execute(select(User.id, User.password_hash)).all())

    with pytest.raises(SeedConflictError):
        _run_seed(
            identity_engine,
            admin_password=SecretStr(token_urlsafe(24)),
            operator_password=operator_password,
        )

    with OrmSession(identity_engine) as session:
        current_hashes = dict(session.execute(select(User.id, User.password_hash)).all())
    assert current_hashes == original_hashes


def test_seed_rejects_production_and_weak_password_before_writing(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    admin_password, operator_password = seed_passwords
    with pytest.raises(SeedSafetyError):
        _run_seed(
            identity_engine,
            environment=AppEnvironment.PRODUCTION,
            admin_password=admin_password,
            operator_password=operator_password,
        )
    with pytest.raises(SeedSafetyError):
        _run_seed(
            identity_engine,
            admin_password=admin_password,
            operator_password=SecretStr("too-short"),
        )
    with pytest.raises(SeedSafetyError):
        _run_seed(
            identity_engine,
            admin_password=admin_password,
            operator_password=admin_password,
        )

    with OrmSession(identity_engine) as session:
        assert session.scalar(select(func.count()).select_from(Organization)) == 0
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_seed_conflict_rolls_back_without_creating_partial_users(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    with OrmSession(identity_engine) as session:
        with session.begin():
            session.add(
                Organization(
                    id=TEST_ORGANIZATION_ID,
                    name="Conflicting synthetic organization",
                )
            )

    with pytest.raises(SeedConflictError):
        _run_seed(
            identity_engine,
            admin_password=seed_passwords[0],
            operator_password=seed_passwords[1],
        )

    with OrmSession(identity_engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
        assert session.scalar(
            select(func.count()).select_from(OrganizationMember)
        ) == 0


def test_normalized_login_conflict_rolls_back_new_seed_rows(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    with OrmSession(identity_engine) as session:
        with session.begin():
            session.add(
                User(
                    login_name=f"  {TEST_ADMIN_LOGIN_NAME.upper()}  ",
                    display_name="Unrelated synthetic user",
                    password_hash=hash_password(SecretStr(token_urlsafe(24))),
                )
            )

    with pytest.raises(SeedConflictError):
        _run_seed(
            identity_engine,
            admin_password=seed_passwords[0],
            operator_password=seed_passwords[1],
        )

    with OrmSession(identity_engine) as session:
        assert session.scalar(select(func.count()).select_from(Organization)) == 0
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(
            select(func.count()).select_from(OrganizationMember)
        ) == 0


def test_seed_recovers_missing_memberships_without_rehashing_users(
    identity_engine: Engine,
    seed_passwords: tuple[SecretStr, SecretStr],
) -> None:
    admin_password, operator_password = seed_passwords
    admin_hash = hash_password(admin_password)
    operator_hash = hash_password(operator_password)
    with OrmSession(identity_engine) as session:
        with session.begin():
            session.add(Organization(id=TEST_ORGANIZATION_ID, name=TEST_ORGANIZATION_NAME))
            session.add_all(
                [
                    User(
                        id=TEST_ADMIN_USER_ID,
                        login_name=TEST_ADMIN_LOGIN_NAME,
                        display_name=TEST_ADMIN_DISPLAY_NAME,
                        password_hash=admin_hash,
                    ),
                    User(
                        id=TEST_OPERATOR_USER_ID,
                        login_name=TEST_OPERATOR_LOGIN_NAME,
                        display_name=TEST_OPERATOR_DISPLAY_NAME,
                        password_hash=operator_hash,
                    ),
                ]
            )

    result = _run_seed(
        identity_engine,
        admin_password=admin_password,
        operator_password=operator_password,
    )

    assert result.created_organizations == 0
    assert result.created_users == 0
    assert result.created_memberships == 2
    with OrmSession(identity_engine) as session:
        hashes = dict(session.execute(select(User.id, User.password_hash)).all())
    assert hashes == {
        TEST_ADMIN_USER_ID: admin_hash,
        TEST_OPERATOR_USER_ID: operator_hash,
    }
