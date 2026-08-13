"""PostgreSQL acceptance for the customer vertical slice."""

import os
from uuid import UUID, uuid4

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
from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _grant(engine: Engine, identity, *codes: str) -> None:
    role = Role(
        id=uuid4(),
        organization_id=identity.organization_id,
        code=f"customer_role_{uuid4().hex}",
        name="Synthetic Customer Role",
    )
    with OrmSession(engine) as session, session.begin():
        permissions = []
        for code in codes:
            permission = session.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(id=uuid4(), code=code, name=f"Synthetic {code}")
                session.add(permission)
            permissions.append(permission)
        session.add(role)
        session.flush()
        session.add_all(
            [RolePermission(role_id=role.id, permission_id=item.id) for item in permissions]
            + [
                OrganizationMemberRole(
                    organization_id=identity.organization_id,
                    organization_member_id=identity.membership_id,
                    role_id=role.id,
                )
            ]
        )


def _client(engine: Engine, identity):
    client = make_auth_client(engine)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(identity.organization_id),
            "login_name": identity.login_name,
            "password": identity.password.get_secret_value(),
        },
    )
    assert response.status_code == 200
    return client


def _payload(code: str, name: str) -> dict[str, str | None]:
    return {
        "code": code,
        "name": name,
        "short_name": f"{name}簡稱",
        "tax_identifier": "12345678",
        "contact_name": "虛構聯絡人",
        "phone": "02-0000-0000",
        "phone_secondary": None,
        "mobile": None,
        "fax": "02-0000-0001",
        "email": "synthetic@example.invalid",
        "postal_code": "000",
        "city": "測試市",
        "address": "測試地址",
        "payment_terms": "月結 30 天（虛構）",
    }


def test_customer_create_search_update_status_and_audit(identity_engine: Engine) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant(identity_engine, identity, "customers.read", "customers.manage")
    client = _client(identity_engine, identity)
    csrf = client.cookies.get("company_system_csrf")

    created = client.post(
        "/api/v1/customers",
        json=_payload(" C001 ", "虛構客戶甲"),
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    customer = created.json()
    assert customer["code"] == "C001"

    found = client.get("/api/v1/customers", params={"keyword": "簡稱"})
    assert found.status_code == 200
    assert found.json()["items"][0]["id"] == customer["id"]

    update_payload = _payload("C001", "虛構客戶乙")
    update_payload["expected_updated_at"] = customer["updated_at"]
    updated = client.put(
        f"/api/v1/customers/{customer['id']}",
        json=update_payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    inactive = client.put(
        f"/api/v1/customers/{customer['id']}/status",
        json={"expected_updated_at": updated.json()["updated_at"], "status": "inactive"},
        headers={"X-CSRF-Token": csrf},
    )
    assert inactive.status_code == 200
    assert inactive.json()["status"] == "inactive"

    with OrmSession(identity_engine) as session:
        actions = session.scalars(
            select(AuditLog.action)
            .where(AuditLog.entity_id == UUID(customer["id"]))
            .order_by(AuditLog.created_at)
        ).all()
        assert actions == ["customer.create", "customer.update", "customer.status_update"]


def test_customer_company_scope_duplicate_and_permissions(identity_engine: Engine) -> None:
    identity_a = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-A-{uuid4()}"))
    identity_b = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-B-{uuid4()}"))
    _grant(identity_engine, identity_a, "customers.read", "customers.manage")
    _grant(identity_engine, identity_b, "customers.read")
    client_a = _client(identity_engine, identity_a)
    csrf_a = client_a.cookies.get("company_system_csrf")
    created = client_a.post(
        "/api/v1/customers",
        json=_payload("C001", "A 公司客戶"),
        headers={"X-CSRF-Token": csrf_a},
    ).json()

    duplicate = client_a.post(
        "/api/v1/customers",
        json=_payload(" c001 ", "重複代號"),
        headers={"X-CSRF-Token": csrf_a},
    )
    client_b = _client(identity_engine, identity_b)
    assert duplicate.status_code == 409
    assert client_b.get("/api/v1/customers").json()["items"] == []
    assert client_b.get(f"/api/v1/customers/{created['id']}").status_code == 404
    assert (
        client_b.post("/api/v1/customers", json=_payload("B001", "B 公司客戶")).status_code == 403
    )
