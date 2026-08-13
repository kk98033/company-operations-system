"""Synthetic helpers shared by identity PostgreSQL acceptance tests."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, Table
from sqlalchemy.exc import IntegrityError

from app.modules.auth.models import User
from app.modules.organizations.models import Organization, OrganizationMember


def assert_insert_rejected(engine: Engine, table: Table, values: dict[str, object]) -> None:
    with engine.connect() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin():
                connection.execute(table.insert(), values)


def seed_identity(engine: Engine) -> tuple[UUID, UUID, UUID, str]:
    organization_id = uuid4()
    user_id = uuid4()
    member_id = uuid4()
    login_name = f"synthetic.operator.{user_id.hex}"
    with engine.begin() as connection:
        connection.execute(
            Organization.__table__.insert(),
            {"id": organization_id, "name": "Synthetic Test Organization"},
        )
        connection.execute(
            User.__table__.insert(),
            {
                "id": user_id,
                "login_name": login_name,
                "display_name": "Synthetic Operator",
                "password_hash": "$argon2id$synthetic-test-hash-only",
            },
        )
        connection.execute(
            OrganizationMember.__table__.insert(),
            {
                "id": member_id,
                "organization_id": organization_id,
                "user_id": user_id,
            },
        )
    return organization_id, user_id, member_id, login_name
