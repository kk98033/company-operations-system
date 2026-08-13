"""PostgreSQL acceptance for scoped and audited company-profile settings."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit.models import AuditLog
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from app.modules.organizations.models import Organization
from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _grant_settings_manage(engine: Engine, *, organization_id, membership_id) -> None:
    permission = Permission(id=uuid4(), code="settings.manage", name="Manage synthetic settings")
    role = Role(
        id=uuid4(),
        organization_id=organization_id,
        code="settings_manager",
        name="Synthetic Settings Manager",
    )
    with OrmSession(engine) as session, session.begin():
        session.add_all([permission, role])
        session.flush()
        session.add_all(
            [
                RolePermission(role_id=role.id, permission_id=permission.id),
                OrganizationMemberRole(
                    organization_id=organization_id,
                    organization_member_id=membership_id,
                    role_id=role.id,
                ),
            ]
        )


def _login(client, identity) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(identity.organization_id),
            "login_name": identity.login_name,
            "password": identity.password.get_secret_value(),
        },
    )
    assert response.status_code == 200


def _profile_payload(profile: dict[str, object]) -> dict[str, object]:
    return {
        "expected_updated_at": profile["updated_at"],
        "name": "Synthetic Company A Updated",
        "tax_identifier": "00000000",
        "representative_name": "Synthetic Representative",
        "phone": "02-0000-0000",
        "fax": "02-0000-0001",
        "email": "synthetic-a@example.invalid",
        "address": "Synthetic Address A",
    }


def test_profile_update_is_company_scoped_permission_guarded_and_audited(
    identity_engine: Engine,
) -> None:
    identity_a = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-A-{uuid4()}"))
    identity_b = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-B-{uuid4()}"))
    _grant_settings_manage(
        identity_engine,
        organization_id=identity_a.organization_id,
        membership_id=identity_a.membership_id,
    )

    client_a = make_auth_client(identity_engine)
    _login(client_a, identity_a)
    initial = client_a.get("/api/v1/organizations/current/profile")
    csrf = client_a.cookies.get("company_system_csrf")
    forged_payload = {
        **_profile_payload(initial.json()),
        "organization_id": str(identity_b.organization_id),
    }
    forged = client_a.put(
        "/api/v1/organizations/current/profile",
        json=forged_payload,
        headers={"X-CSRF-Token": csrf},
    )
    updated = client_a.put(
        "/api/v1/organizations/current/profile",
        json=_profile_payload(initial.json()),
        headers={"X-CSRF-Token": csrf},
    )

    assert initial.status_code == 200
    assert forged.status_code == 422
    assert updated.status_code == 200
    assert updated.json()["id"] == str(identity_a.organization_id)
    assert updated.json()["name"] == "Synthetic Company A Updated"
    assert updated.json()["logo"] is None
    with OrmSession(identity_engine) as session:
        company_b = session.get(Organization, identity_b.organization_id)
        event = session.execute(
            select(AuditLog).where(
                AuditLog.organization_id == identity_a.organization_id,
                AuditLog.action == "organization.profile_update",
            )
        ).scalar_one()
        assert company_b is not None
        assert company_b.name.startswith("Synthetic Organization")
        assert event.actor_user_id == identity_a.user_id
        assert event.after_data["email"] == "synthetic-a@example.invalid"

    client_b = make_auth_client(identity_engine)
    _login(client_b, identity_b)
    denied = client_b.get("/api/v1/organizations/current/profile")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PERMISSION_DENIED"


def test_profile_update_requires_csrf_and_rejects_stale_editor(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant_settings_manage(
        identity_engine,
        organization_id=identity.organization_id,
        membership_id=identity.membership_id,
    )
    client = make_auth_client(identity_engine)
    _login(client, identity)
    initial = client.get("/api/v1/organizations/current/profile").json()
    payload = _profile_payload(initial)

    missing_csrf = client.put("/api/v1/organizations/current/profile", json=payload)
    first = client.put(
        "/api/v1/organizations/current/profile",
        json=payload,
        headers={"X-CSRF-Token": client.cookies.get("company_system_csrf")},
    )
    stale = client.put(
        "/api/v1/organizations/current/profile",
        json=payload,
        headers={"X-CSRF-Token": client.cookies.get("company_system_csrf")},
    )

    assert missing_csrf.status_code == 403
    assert first.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "ORGANIZATION_PROFILE_CONFLICT"


def test_logo_metadata_is_read_only_and_must_be_complete(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant_settings_manage(
        identity_engine,
        organization_id=identity.organization_id,
        membership_id=identity.membership_id,
    )
    with OrmSession(identity_engine) as session, session.begin():
        organization = session.get(Organization, identity.organization_id)
        assert organization is not None
        organization.logo_object_key = "synthetic/logo.png"
        organization.logo_content_type = "image/png"
        organization.logo_original_filename = "synthetic-logo.png"
        organization.logo_sha256 = "a" * 64

    client = make_auth_client(identity_engine)
    _login(client, identity)
    response = client.get("/api/v1/organizations/current/profile")

    assert response.status_code == 200
    assert response.json()["logo"] == {
        "content_type": "image/png",
        "original_filename": "synthetic-logo.png",
        "sha256": "a" * 64,
    }
    update_schema = client.get("/openapi.json").json()["components"]["schemas"][
        "OrganizationProfileUpdate"
    ]
    assert "logo" not in update_schema["properties"]
    assert "logo_object_key" not in response.text
