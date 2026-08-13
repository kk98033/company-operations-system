"""PostgreSQL acceptance for vendors, paper catalogs, and fixed processes."""

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
        code=f"master_role_{uuid4().hex}",
        name="Synthetic Master Role",
    )
    with OrmSession(engine) as session, session.begin():
        permissions = []
        for code in codes:
            permission = session.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(id=uuid4(), code=code, name=f"Synthetic {code}")
                session.add(permission)
                session.flush()
            permissions.append(permission)
        session.add(role)
        session.flush()
        session.add_all(
            [
                *(RolePermission(role_id=role.id, permission_id=item.id) for item in permissions),
                OrganizationMemberRole(
                    organization_id=identity.organization_id,
                    organization_member_id=identity.membership_id,
                    role_id=role.id,
                ),
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


def _vendor_payload(code: str, name: str) -> dict:
    return {
        "code": code,
        "name": name,
        "short_name": name,
        "category": "supplier",
        "contact_name": "虛構聯絡人",
        "phone": "02-0000-0000",
        "phone_secondary": None,
        "mobile": None,
        "fax": None,
        "email": "synthetic@example.invalid",
        "postal_code": "000",
        "city": "測試市",
        "address": "測試地址",
        "settlement_day": 25,
    }


def test_vendor_and_paper_catalog_commands(identity_engine: Engine) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant(identity_engine, identity, "master_data.read", "master_data.manage")
    client = _client(identity_engine, identity)
    headers = {"X-CSRF-Token": client.cookies.get("company_system_csrf")}

    vendor = client.post(
        "/api/v1/vendors",
        json=_vendor_payload("V001", "虛構紙張供應商"),
        headers=headers,
    )
    assert vendor.status_code == 201
    assert (
        client.get("/api/v1/vendors", params={"keyword": "供應商"}).json()["items"][0]["id"]
        == vendor.json()["id"]
    )
    assert (
        client.post(
            "/api/v1/vendors",
            json=_vendor_payload(" v001 ", "重複供應商"),
            headers=headers,
        ).status_code
        == 409
    )

    paper_type = client.post(
        "/api/v1/master-data/paper-types",
        json={"code": "P001", "name": "虛構紙質", "sort_order": 1},
        headers=headers,
    )
    assert paper_type.status_code == 201
    assert (
        client.post(
            "/api/v1/master-data/paper-types",
            json={"code": "P002", "name": " 虛構紙質 ", "sort_order": 2},
            headers=headers,
        ).status_code
        == 409
    )
    paper_mill = client.post(
        "/api/v1/master-data/paper-mills",
        json={"code": "M001", "name": "虛構紙廠", "sort_order": 1},
        headers=headers,
    )
    assert paper_mill.status_code == 201

    inactive = client.put(
        f"/api/v1/master-data/paper-types/{paper_type.json()['id']}/status",
        json={"expected_updated_at": paper_type.json()["updated_at"], "status": "inactive"},
        headers=headers,
    )
    assert inactive.status_code == 200
    assert inactive.json()["status"] == "inactive"


def test_confirmed_processes_are_seeded_in_fixed_order(identity_engine: Engine) -> None:
    identity = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-{uuid4()}"))
    _grant(identity_engine, identity, "master_data.read", "master_data.manage")
    client = _client(identity_engine, identity)
    processes = client.get("/api/v1/master-data/process-definitions")
    assert processes.status_code == 200
    assert [item["name"] for item in processes.json()] == [
        "美工",
        "輸出",
        "製版",
        "打樣",
        "印刷",
        "上光",
        "裱紙",
        "模具",
        "軋型",
        "加工",
        "糊邊",
        "運送",
        "其他",
    ]
    first = processes.json()[0]
    updated = client.put(
        f"/api/v1/master-data/process-definitions/{first['id']}/status",
        json={"expected_updated_at": first["updated_at"], "status": "inactive"},
        headers={"X-CSRF-Token": client.cookies.get("company_system_csrf")},
    )
    assert updated.status_code == 200
    assert updated.json()["code"] == "artwork"
    assert updated.json()["status"] == "inactive"


def test_master_data_is_company_scoped_and_deny_by_default(identity_engine: Engine) -> None:
    identity_a = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-A-{uuid4()}"))
    identity_b = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-B-{uuid4()}"))
    _grant(identity_engine, identity_a, "master_data.read", "master_data.manage")
    _grant(identity_engine, identity_b, "master_data.read")
    client_a = _client(identity_engine, identity_a)
    client_b = _client(identity_engine, identity_b)
    created = client_a.post(
        "/api/v1/vendors",
        json=_vendor_payload("V001", "A 公司虛構供應商"),
        headers={"X-CSRF-Token": client_a.cookies.get("company_system_csrf")},
    )
    assert created.status_code == 201
    assert client_b.get("/api/v1/vendors").json()["items"] == []
    assert (
        client_b.post("/api/v1/vendors", json=_vendor_payload("V001", "B 公司")).status_code == 403
    )
