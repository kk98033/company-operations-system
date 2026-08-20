"""PostgreSQL acceptance for production cases and work orders."""

import os
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from tests.integration.auth_test_support import create_auth_identity, make_auth_client
from tests.integration.work_order_test_support import grant, setup_company, work_order_payload

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def test_direct_work_order_lifecycle_snapshot_search_and_attachment(
    identity_engine: Engine,
) -> None:
    _identity, client, csrf, customer = setup_company(identity_engine, "FLOW")
    created = client.post(
        "/api/v1/work-orders",
        json=work_order_payload(customer["id"]),
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["document_number"] == "WO-20260813-001"
    assert order["status"] == "draft"
    case = client.get(f"/api/v1/cases/{order['case_id']}").json()
    assert case["case_number"] == "CASE-20260813-001"
    assert [item["id"] for item in case["work_orders"]] == [order["id"]]

    updated_payload = work_order_payload(customer["id"], "2026-08-14")
    updated_payload.pop("case_id")
    updated_payload["expected_updated_at"] = order["updated_at"]
    updated = client.put(
        f"/api/v1/work-orders/{order['id']}",
        json=updated_payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200, updated.text
    order = updated.json()
    assert order["document_number"] == "WO-20260813-001"
    assert order["order_date"] == "2026-08-14"

    content = b"synthetic-png-content"
    uploaded = client.post(
        f"/api/v1/work-orders/{order['id']}/attachments",
        params={"filename": "layout.png"},
        content=content,
        headers={"Content-Type": "image/png", "X-CSRF-Token": csrf},
    )
    assert uploaded.status_code == 201, uploaded.text
    attachment = uploaded.json()

    confirmed = client.post(
        f"/api/v1/work-orders/{order['id']}/confirm",
        json={"expected_updated_at": order["updated_at"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert confirmed.status_code == 200, confirmed.text
    order = confirmed.json()
    assert order["status"] == "confirmed"
    assert order["document_snapshot"]["status"] == "confirmed"
    assert len(order["document_snapshot"]["processes"]) == 9
    assert order["print_metadata"]["orientation"] == "portrait"
    assert client.get("/api/v1/work-orders", params={"keyword": "20.50"}).status_code == 200
    result = client.get("/api/v1/work-orders", params={"keyword": "虛構彩盒"}).json()
    assert result["meta"]["pagination"]["total_items"] == 1
    assert result["items"][0]["plate_fee"] == "7000.0000"

    downloaded = client.get(f"/api/v1/work-orders/{order['id']}/attachments/{attachment['id']}")
    assert downloaded.content == content
    assert downloaded.headers["cache-control"] == "private, no-store"
    with Session(identity_engine) as session:
        download_event = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "work_order.attachment.download"
            )
        )
    assert download_event is not None
    assert download_event.entity_id == UUID(attachment["id"])
    assert (
        client.delete(
            f"/api/v1/work-orders/{order['id']}/attachments/{attachment['id']}",
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )
    assert len(client.get(f"/api/v1/work-orders/{order['id']}/attachments").json()) == 1


def test_confirmed_quotation_converts_atomically_and_idempotently(
    identity_engine: Engine,
) -> None:
    _identity, client, csrf, customer = setup_company(identity_engine, "CONVERT")
    quote_payload = {
        "quotation_date": "2026-08-15",
        "customer_id": customer["id"],
        "notes": "轉單虛構備註",
        "items": [
            {"product_name": "虛構品項 A", "quantity": "100", "unit_price": "3.5"},
            {"product_name": "虛構品項 B", "quantity": "200", "unit_price": "4.5"},
        ],
    }
    quote = client.post(
        "/api/v1/quotations",
        json=quote_payload,
        headers={"X-CSRF-Token": csrf},
    ).json()
    assert (
        client.post(
            "/api/v1/cases/from-quotation/convert",
            json={"quotation_id": quote["id"], "item_ids": [item["id"] for item in quote["items"]]},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )
    quote = client.post(
        f"/api/v1/quotations/{quote['id']}/confirm",
        json={"expected_updated_at": quote["updated_at"]},
        headers={"X-CSRF-Token": csrf},
    ).json()
    request = {"quotation_id": quote["id"], "item_ids": [item["id"] for item in quote["items"]]}
    converted = client.post(
        "/api/v1/cases/from-quotation/convert",
        json=request,
        headers={"X-CSRF-Token": csrf},
    )
    assert converted.status_code == 201, converted.text
    case = converted.json()
    assert case["source_quotation_id"] == quote["id"]
    assert [item["product_name"] for item in case["work_orders"]] == [
        "虛構品項 A",
        "虛構品項 B",
    ]
    repeated = client.post(
        "/api/v1/cases/from-quotation/convert",
        json=request,
        headers={"X-CSRF-Token": csrf},
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == case["id"]
    partial = {"quotation_id": quote["id"], "item_ids": [quote["items"][0]["id"]]}
    assert (
        client.post(
            "/api/v1/cases/from-quotation/convert",
            json=partial,
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )


def test_work_order_scope_and_capability_are_enforced(identity_engine: Engine) -> None:
    _a, client_a, csrf_a, customer_a = setup_company(identity_engine, "SCOPE-A")
    _b, client_b, _csrf_b, _customer_b = setup_company(identity_engine, "SCOPE-B")
    order = client_a.post(
        "/api/v1/work-orders",
        json=work_order_payload(customer_a["id"]),
        headers={"X-CSRF-Token": csrf_a},
    ).json()
    assert client_b.get(f"/api/v1/work-orders/{order['id']}").status_code == 404

    read_only = create_auth_identity(identity_engine, password=SecretStr(f"Synthetic-RO-{uuid4()}"))
    grant(identity_engine, read_only, "work_orders.read")
    client_ro = make_auth_client(identity_engine)
    assert (
        client_ro.post(
            "/api/v1/auth/login",
            json={
                "organization_id": str(read_only.organization_id),
                "login_name": read_only.login_name,
                "password": read_only.password.get_secret_value(),
            },
        ).status_code
        == 200
    )
    assert client_ro.get("/api/v1/work-orders").status_code == 200
    assert (
        client_ro.post("/api/v1/work-orders", json=work_order_payload(customer_a["id"])).status_code
        == 403
    )
