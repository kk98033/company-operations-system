"""PostgreSQL acceptance for scoped company defaults and fixed policies."""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit.models import AuditLog
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from app.modules.organizations.models import OrganizationSettings
from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _grant_settings_manage(engine: Engine, identity) -> None:
    permission = Permission(id=uuid4(), code="settings.manage", name="Manage synthetic settings")
    role = Role(
        id=uuid4(),
        organization_id=identity.organization_id,
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
                    organization_id=identity.organization_id,
                    organization_member_id=identity.membership_id,
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


def test_settings_defaults_and_fixed_company_policies(identity_engine: Engine) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant_settings_manage(identity_engine, identity)
    client = make_auth_client(identity_engine)
    _login(client, identity)

    response = client.get("/api/v1/organizations/current/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == str(identity.organization_id)
    assert body["statement_tax"] == {
        "enabled": False,
        "tax_rate_percent": None,
        "rounding_scope": None,
        "rounding_decimal_places": None,
        "calculation_status": "pending_phase_8_uat",
    }
    assert [policy["format"] for policy in body["document_numbering"]] == [
        "QUO-YYYYMMDD-SS",
        "CASE-YYYYMMDD-SSS",
        "WO-YYYYMMDD-SSS",
        "SHP-YYYYMM-SSS",
        "PRC-YYYYMMDD-SSS",
        "STM-YYYYMM-SSS",
        "RCT-YYYYMMDD-SSS",
    ]
    assert [(item["label"], item["orientation"]) for item in body["printing"]] == [
        ("報價單", "landscape"),
        ("工單", "portrait"),
        ("對帳單", None),
    ]


def test_settings_update_is_scoped_audited_and_conflict_safe(
    identity_engine: Engine,
) -> None:
    identity_a = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-A-{uuid4()}"))
    identity_b = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-B-{uuid4()}"))
    _grant_settings_manage(identity_engine, identity_a)
    client = make_auth_client(identity_engine)
    _login(client, identity_a)
    initial = client.get("/api/v1/organizations/current/settings").json()
    payload = {
        "expected_updated_at": initial["updated_at"],
        "statement_tax_default_enabled": True,
        "statement_tax_rate_percent": "5.0000",
        "statement_rounding_scope": "per_line",
        "statement_rounding_decimal_places": 0,
    }
    csrf = client.cookies.get("company_system_csrf")

    missing_csrf = client.put("/api/v1/organizations/current/settings", json=payload)
    updated = client.put(
        "/api/v1/organizations/current/settings",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    stale = client.put(
        "/api/v1/organizations/current/settings",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )

    assert missing_csrf.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["statement_tax"]["tax_rate_percent"] == "5.0000"
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "ORGANIZATION_SETTINGS_CONFLICT"
    with OrmSession(identity_engine) as session:
        company_b = session.get(OrganizationSettings, identity_b.organization_id)
        event = session.execute(
            select(AuditLog).where(
                AuditLog.organization_id == identity_a.organization_id,
                AuditLog.action == "organization.settings_update",
            )
        ).scalar_one()
        assert company_b is not None
        assert company_b.statement_tax_default_enabled is False
        assert event.before_data["statement_tax_default_enabled"] is False
        assert event.after_data["statement_rounding_scope"] == "per_line"


def test_settings_validation_and_database_constraints(identity_engine: Engine) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant_settings_manage(identity_engine, identity)
    client = make_auth_client(identity_engine)
    _login(client, identity)
    initial = client.get("/api/v1/organizations/current/settings").json()

    incomplete = client.put(
        "/api/v1/organizations/current/settings",
        json={
            "expected_updated_at": initial["updated_at"],
            "statement_tax_default_enabled": True,
            "statement_tax_rate_percent": "5.0000",
            "statement_rounding_scope": None,
            "statement_rounding_decimal_places": None,
        },
        headers={"X-CSRF-Token": client.cookies.get("company_system_csrf")},
    )
    assert incomplete.status_code == 422

    with pytest.raises(IntegrityError), OrmSession(identity_engine) as session:
        settings = session.get(OrganizationSettings, identity.organization_id)
        assert settings is not None
        settings.statement_tax_rate_percent = Decimal("5")
        session.commit()
