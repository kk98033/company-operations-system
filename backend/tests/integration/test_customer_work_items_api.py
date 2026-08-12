"""PostgreSQL acceptance for reusable customer work items."""

import os
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as OrmSession

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
        code=f"work_item_{uuid4().hex}",
        name="Synthetic Work Item Role",
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


def _customer(client, csrf: str, code: str) -> dict:
    response = client.post(
        "/api/v1/customers",
        json={"code": code, "name": f"虛構客戶 {code}"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    return response.json()


def test_work_item_create_search_status_and_duplicate(identity_engine: Engine) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant(identity_engine, identity, "customers.read", "customers.manage")
    client = _client(identity_engine, identity)
    csrf = client.cookies.get("company_system_csrf")
    customer = _customer(client, csrf, "C-WORK")
    url = f"/api/v1/customers/{customer['id']}/work-items"

    created = client.post(
        url,
        json={
            "code": " BOX-A ",
            "name": "虛構彩盒",
            "specification": "350g 紙材",
            "unit_price": "12.5000",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    item = created.json()
    assert item["source"] == "manual"
    assert item["legacy_source_key"] is None
    assert client.get(url, params={"keyword": "350g"}).json()["items"][0]["id"] == item["id"]
    duplicate = client.post(
        url, json={"code": "box-a", "name": "重複"}, headers={"X-CSRF-Token": csrf}
    )
    assert duplicate.status_code == 409
    inactive = client.put(
        f"{url}/{item['id']}/status",
        json={"status": "inactive", "expected_updated_at": item["updated_at"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert inactive.status_code == 200
    assert inactive.json()["status"] == "inactive"


def test_work_item_company_scope_and_read_only_permission(identity_engine: Engine) -> None:
    identity_a = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-A-{uuid4()}"))
    identity_b = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-B-{uuid4()}"))
    _grant(identity_engine, identity_a, "customers.read", "customers.manage")
    _grant(identity_engine, identity_b, "customers.read")
    client_a = _client(identity_engine, identity_a)
    csrf_a = client_a.cookies.get("company_system_csrf")
    customer = _customer(client_a, csrf_a, "A-WORK")
    client_b = _client(identity_engine, identity_b)
    assert client_b.get(f"/api/v1/customers/{customer['id']}/work-items").status_code == 404
    assert (
        client_b.post(
            f"/api/v1/customers/{customer['id']}/work-items", json={"code": "X", "name": "X"}
        ).status_code
        == 403
    )
