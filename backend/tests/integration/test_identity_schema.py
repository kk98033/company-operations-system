"""PostgreSQL acceptance tests for organizations, users, and memberships."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import Engine, inspect

from app.modules.auth.models import User
from app.modules.organizations.models import Organization, OrganizationMember
from tests.integration.identity_test_support import (
    assert_insert_rejected,
    seed_identity,
)

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def test_identity_schema_has_expected_constraints_and_indexes(
    identity_engine: Engine,
) -> None:
    database_inspector = inspect(identity_engine)

    assert {
        "organizations",
        "users",
        "organization_members",
        "sessions",
    } <= set(database_inspector.get_table_names())
    user_indexes = {
        index["name"]: index for index in database_inspector.get_indexes("users")
    }
    normalized_login_index = user_indexes["uq_users_login_name_normalized"]
    assert normalized_login_index["unique"] is True
    assert "lower" in " ".join(normalized_login_index["expressions"])
    assert "btrim" in " ".join(normalized_login_index["expressions"])
    assert "uq_organization_members_organization_id_user_id" in {
        constraint["name"]
        for constraint in database_inspector.get_unique_constraints(
            "organization_members"
        )
    }
    assert "uq_sessions_token_digest" in {
        constraint["name"]
        for constraint in database_inspector.get_unique_constraints("sessions")
    }
    member_indexes = {
        index["name"]: index
        for index in database_inspector.get_indexes("organization_members")
    }
    assert member_indexes[
        "ix_organization_members_organization_id_status"
    ]["column_names"] == ["organization_id", "status"]
    assert member_indexes[
        "ix_organization_members_user_id_status"
    ]["column_names"] == ["user_id", "status"]

    session_indexes = {
        index["name"]: index
        for index in database_inspector.get_indexes("sessions")
    }
    assert session_indexes[
        "ix_sessions_organization_member_id_expires_at"
    ]["column_names"] == ["organization_member_id", "expires_at"]
    assert session_indexes["ix_sessions_expires_at"]["column_names"] == [
        "expires_at"
    ]

    user_columns = {
        column["name"] for column in database_inspector.get_columns("users")
    }
    session_columns = {
        column["name"] for column in database_inspector.get_columns("sessions")
    }
    assert "password" not in user_columns
    assert "password_hash" in user_columns
    assert "token" not in session_columns
    assert "token_digest" in session_columns


def test_login_and_membership_uniqueness_is_enforced(
    identity_engine: Engine,
) -> None:
    organization_id, user_id, _, login_name = seed_identity(identity_engine)

    assert_insert_rejected(
        identity_engine,
        User.__table__,
        {
            "id": uuid4(),
            "login_name": f"  {login_name.upper()}  ",
            "display_name": "Duplicate Synthetic Operator",
            "password_hash": "$argon2id$another-synthetic-hash",
        },
    )
    assert_insert_rejected(
        identity_engine,
        OrganizationMember.__table__,
        {
            "id": uuid4(),
            "organization_id": organization_id,
            "user_id": user_id,
        },
    )


def test_blank_and_invalid_identity_values_are_rejected(
    identity_engine: Engine,
) -> None:
    assert_insert_rejected(
        identity_engine,
        Organization.__table__,
        {"id": uuid4(), "name": "   "},
    )
    assert_insert_rejected(
        identity_engine,
        User.__table__,
        {
            "id": uuid4(),
            "login_name": "synthetic.invalid",
            "display_name": "Synthetic Invalid",
            "password_hash": "   ",
        },
    )
    for blank_field in ("login_name", "display_name"):
        values = {
            "id": uuid4(),
            "login_name": "synthetic.blank-login",
            "display_name": "Synthetic Blank Display",
            "password_hash": "$argon2id$synthetic-hash",
        }
        values[blank_field] = "   "
        assert_insert_rejected(identity_engine, User.__table__, values)
    assert_insert_rejected(
        identity_engine,
        User.__table__,
        {
            "id": uuid4(),
            "login_name": "synthetic.invalid-status",
            "display_name": "Synthetic Invalid Status",
            "password_hash": "$argon2id$synthetic-hash",
            "status": "unknown",
        },
    )
    assert_insert_rejected(
        identity_engine,
        Organization.__table__,
        {"id": uuid4(), "name": "Synthetic Invalid Org", "status": "unknown"},
    )
    organization_id, user_id, _, _ = seed_identity(identity_engine)
    assert_insert_rejected(
        identity_engine,
        OrganizationMember.__table__,
        {
            "id": uuid4(),
            "organization_id": organization_id,
            "user_id": user_id,
            "status": "unknown",
        },
    )


def test_membership_allows_an_existing_user_in_another_organization(
    identity_engine: Engine,
) -> None:
    _, user_id, _, _ = seed_identity(identity_engine)
    second_organization_id = uuid4()
    with identity_engine.begin() as connection:
        connection.execute(
            Organization.__table__.insert(),
            {"id": second_organization_id, "name": "Synthetic Organization B"},
        )
        connection.execute(
            OrganizationMember.__table__.insert(),
            {
                "id": uuid4(),
                "organization_id": second_organization_id,
                "user_id": user_id,
            },
        )


def test_membership_foreign_keys_are_enforced(identity_engine: Engine) -> None:
    organization_id, user_id, _, _ = seed_identity(identity_engine)
    for values in (
        {
            "id": uuid4(),
            "organization_id": uuid4(),
            "user_id": user_id,
        },
        {
            "id": uuid4(),
            "organization_id": organization_id,
            "user_id": uuid4(),
        },
    ):
        assert_insert_rejected(
            identity_engine, OrganizationMember.__table__, values
        )
