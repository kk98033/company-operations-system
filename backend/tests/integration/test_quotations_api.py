"""PostgreSQL acceptance for the quotation vertical slice."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import UUID, uuid4

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
from app.modules.quotations.models import DocumentSequence, Quotation
from app.modules.quotations.service import _allocate_number
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
        code=f"quote_{uuid4().hex}",
        name="Synthetic Quotation Role",
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


def _setup(engine: Engine, suffix: str):
    identity = create_auth_identity(engine, password=SecretStr(f"Synthetic-{suffix}-{uuid4()}"))
    _grant(
        engine,
        identity,
        "customers.read",
        "customers.manage",
        "quotations.read",
        "quotations.manage",
        "quotations.confirm",
    )
    client = _client(engine, identity)
    csrf = client.cookies.get("company_system_csrf")
    customer = client.post(
        "/api/v1/customers",
        json={
            "code": f"C-{suffix}",
            "name": f"虛構客戶 {suffix}",
            "contact_name": "原聯絡人",
            "phone": "02-0000",
            "fax": "02-0001",
            "address": "原地址",
        },
        headers={"X-CSRF-Token": csrf},
    ).json()
    return identity, client, csrf, customer


def _payload(customer_id: str, quotation_date: str = "2026-08-13") -> dict:
    return {
        "quotation_date": quotation_date,
        "customer_id": customer_id,
        "notes": "整張備註",
        "items": [
            {
                "product_name": "虛構彩盒",
                "size": "100x100mm",
                "paper": "350g",
                "color": "4/4",
                "coating": "亮膜",
                "quantity": "1000",
                "plate_fee": "7000.00",
                "die_fee": "3500.00",
                "unit_price": "20.00",
                "note": "明細附註",
            },
            {
                "product_name": "虛構卡片",
                "quantity": "500",
                "plate_fee": "0",
                "die_fee": "0",
                "unit_price": "5.25",
            },
        ],
    }


def test_create_update_clone_confirm_and_snapshot(identity_engine: Engine) -> None:
    _identity, client, csrf, customer = _setup(identity_engine, "FLOW")
    created = client.post(
        "/api/v1/quotations", json=_payload(customer["id"]), headers={"X-CSRF-Token": csrf}
    )
    assert created.status_code == 201
    quote = created.json()
    assert quote["document_number"] == "QUO-20260813-01"
    assert [item["line_number"] for item in quote["items"]] == [1, 2]
    assert "tax" not in quote
    customer_update = {
        key: customer.get(key)
        for key in [
            "code",
            "name",
            "short_name",
            "tax_identifier",
            "contact_name",
            "phone",
            "phone_secondary",
            "mobile",
            "fax",
            "email",
            "postal_code",
            "city",
            "address",
            "payment_terms",
        ]
    }
    customer_update.update(
        {"contact_name": "新聯絡人", "expected_updated_at": customer["updated_at"]}
    )
    assert (
        client.put(
            f"/api/v1/customers/{customer['id']}",
            json=customer_update,
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 200
    )
    update = _payload(customer["id"], "2026-08-14")
    update["expected_updated_at"] = quote["updated_at"]
    updated = client.put(
        f"/api/v1/quotations/{quote['id']}", json=update, headers={"X-CSRF-Token": csrf}
    )
    assert updated.status_code == 200
    assert updated.json()["document_number"] == "QUO-20260813-01"
    assert updated.json()["customer_snapshot"]["contact_name"] == "原聯絡人"
    cloned = client.post(
        f"/api/v1/quotations/{quote['id']}/clone",
        json={"quotation_date": "2026-08-13"},
        headers={"X-CSRF-Token": csrf},
    )
    assert cloned.status_code == 201
    assert cloned.json()["document_number"] == "QUO-20260813-02"
    assert cloned.json()["source_quotation_id"] == quote["id"]
    confirmed = client.post(
        f"/api/v1/quotations/{quote['id']}/confirm",
        json={"expected_updated_at": updated.json()["updated_at"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["print_metadata"]["orientation"] == "landscape"
    assert confirmed.json()["document_snapshot"]["items"][0]["note"] == "明細附註"
    assert (
        client.put(
            f"/api/v1/quotations/{quote['id']}",
            json={**update, "expected_updated_at": confirmed.json()["updated_at"]},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )
    voided = client.post(
        f"/api/v1/quotations/{quote['id']}/void",
        json={
            "expected_updated_at": confirmed.json()["updated_at"],
            "reason": "客戶取消（虛構測試）",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert voided.status_code == 200
    assert voided.json()["status"] == "void"
    assert voided.json()["void_reason"] == "客戶取消（虛構測試）"
    assert voided.json()["confirmed_at"] == confirmed.json()["confirmed_at"]
    replacement = client.post(
        "/api/v1/quotations",
        json=_payload(customer["id"]),
        headers={"X-CSRF-Token": csrf},
    )
    assert replacement.status_code == 201
    assert replacement.json()["document_number"] == "QUO-20260813-03"


def test_number_period_search_scope_and_permissions(identity_engine: Engine) -> None:
    _a, client_a, csrf_a, customer_a = _setup(identity_engine, "A")
    _b, client_b, _csrf_b, _customer_b = _setup(identity_engine, "B")
    first = client_a.post(
        "/api/v1/quotations",
        json=_payload(customer_a["id"], "2026-08-15"),
        headers={"X-CSRF-Token": csrf_a},
    ).json()
    next_day = client_a.post(
        "/api/v1/quotations",
        json=_payload(customer_a["id"], "2026-08-16"),
        headers={"X-CSRF-Token": csrf_a},
    ).json()
    assert first["document_number"] == "QUO-20260815-01"
    assert next_day["document_number"] == "QUO-20260816-01"
    assert (
        client_a.get("/api/v1/quotations", params={"keyword": "虛構客戶 A"}).json()["meta"][
            "pagination"
        ]["total_items"]
        == 2
    )
    assert client_b.get(f"/api/v1/quotations/{first['id']}").status_code == 404
    read_only = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-RO-{uuid4()}"))
    _grant(identity_engine, read_only, "quotations.read")
    client_ro = _client(identity_engine, read_only)
    assert client_ro.post("/api/v1/quotations", json=_payload(customer_a["id"])).status_code == 403


def test_number_allocation_is_atomic_and_exhaustion_is_explicit(identity_engine: Engine) -> None:
    identity, client, csrf, customer = _setup(identity_engine, "NUMBER")

    def allocate() -> str:
        with OrmSession(identity_engine) as session, session.begin():
            return _allocate_number(session, identity.organization_id, date(2026, 8, 19))

    with ThreadPoolExecutor(max_workers=8) as executor:
        numbers = list(executor.map(lambda _index: allocate(), range(8)))
    assert sorted(numbers) == [f"QUO-20260819-{index:02d}" for index in range(1, 9)]

    with OrmSession(identity_engine) as session, session.begin():
        session.add(
            DocumentSequence(
                organization_id=identity.organization_id,
                document_type="quotation",
                period_key="20260820",
                next_value=100,
            )
        )
    exhausted = client.post(
        "/api/v1/quotations",
        json=_payload(customer["id"], "2026-08-20"),
        headers={"X-CSRF-Token": csrf},
    )
    assert exhausted.status_code == 409
    assert exhausted.json()["error"]["code"] == "QUOTATION_NUMBER_EXHAUSTED"


def test_legacy_number_is_searchable_without_rewriting(identity_engine: Engine) -> None:
    identity, client, csrf, customer = _setup(identity_engine, "LEGACY")
    created = client.post(
        "/api/v1/quotations",
        json=_payload(customer["id"], "2026-08-21"),
        headers={"X-CSRF-Token": csrf},
    ).json()
    with OrmSession(identity_engine) as session, session.begin():
        row = session.get(Quotation, UUID(created["id"]))
        assert row is not None and row.organization_id == identity.organization_id
        row.legacy_document_number = "26042701"
        row.legacy_source_table = "b_replay1"
        row.legacy_source_key = "synthetic-legacy-key"
    result = client.get("/api/v1/quotations", params={"keyword": "26042701"})
    assert result.status_code == 200
    assert result.json()["items"][0]["legacy_document_number"] == "26042701"
