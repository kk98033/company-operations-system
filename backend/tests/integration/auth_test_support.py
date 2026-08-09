"""Synthetic identity and API helpers for authentication integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.core.database import DatabaseResources
from app.main import create_app
from app.modules.auth.models import User
from app.modules.auth.passwords import hash_password
from app.modules.organizations.models import Organization, OrganizationMember
from tests.settings_factory import make_test_settings


@dataclass(frozen=True, slots=True)
class SyntheticAuthIdentity:
    organization_id: UUID
    user_id: UUID
    membership_id: UUID
    login_name: str
    password: SecretStr
    password_hash: str


def create_auth_identity(
    engine: Engine,
    *,
    password: SecretStr,
) -> SyntheticAuthIdentity:
    organization_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()
    login_name = f"synthetic.login.{user_id.hex}"
    password_hash = hash_password(password)
    with engine.begin() as connection:
        connection.execute(
            Organization.__table__.insert(),
            {
                "id": organization_id,
                "name": f"Synthetic Organization {organization_id.hex}",
            },
        )
        connection.execute(
            User.__table__.insert(),
            {
                "id": user_id,
                "login_name": login_name,
                "display_name": "Synthetic Auth Operator",
                "password_hash": password_hash,
            },
        )
        connection.execute(
            OrganizationMember.__table__.insert(),
            {
                "id": membership_id,
                "organization_id": organization_id,
                "user_id": user_id,
            },
        )
    return SyntheticAuthIdentity(
        organization_id=organization_id,
        user_id=user_id,
        membership_id=membership_id,
        login_name=login_name,
        password=password,
        password_hash=password_hash,
    )


def make_auth_client(engine: Engine) -> TestClient:
    resources = DatabaseResources(
        engine=engine,
        session_factory=sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        ),
    )
    return TestClient(
        create_app(
            settings=make_test_settings(),
            database_resources=resources,
            readiness_checks=[],
        )
    )
