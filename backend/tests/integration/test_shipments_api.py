"""PostgreSQL acceptance for Phase 6 shipment and inventory transactions."""

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.modules.production.models import FinalCompletionEntry, InventoryLedgerEntry
from app.modules.shipments.models import Shipment, ShipmentItem
from tests.integration.work_order_test_support import setup_company, work_order_payload

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1", reason="requires isolated PostgreSQL"
    ),
]


def _order_with_inventory(engine: Engine, suffix: str, quantity: str):
    identity, client, csrf, customer = setup_company(engine, suffix)
    created = client.post(
        "/api/v1/work-orders",
        json=work_order_payload(customer["id"]),
        headers={"X-CSRF-Token": csrf},
    ).json()
    confirmed = client.post(
        f"/api/v1/work-orders/{created['id']}/confirm",
        json={"expected_updated_at": created["updated_at"]},
        headers={"X-CSRF-Token": csrf},
    ).json()
    for event_type in ("start", "complete"):
        response = client.post(
            f"/api/v1/production/work-orders/{created['id']}/process-events",
            json={
                "process_code": "transport",
                "event_type": event_type,
                "idempotency_key": str(uuid4()),
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 201, response.text
    if Decimal(quantity) > 0:
        response = client.post(
            f"/api/v1/production/work-orders/{created['id']}/final-completions",
            json={"quantity": quantity, "reason": "虛構實際完工", "idempotency_key": str(uuid4())},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 201, response.text
    return identity, client, csrf, customer, confirmed


def _draft(client, csrf: str, customer_id: str, order_id: str, delivered: str, spare: str = "0"):
    return client.post(
        "/api/v1/shipments",
        json={
            "shipment_date": "2026-08-13",
            "customer_id": customer_id,
            "delivery_address": "虛構測試地址",
            "notes": "虛構出貨測試",
            "items": [
                {
                    "work_order_id": order_id,
                    "delivered_quantity": delivered,
                    "spare_quantity": spare,
                }
            ],
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )


def _confirm(client, csrf: str, draft: dict, completions=None, key=None):
    return client.post(
        f"/api/v1/shipments/{draft['id']}/confirm",
        json={
            "expected_version": draft["version"],
            "idempotency_key": str(key or uuid4()),
            "completions": completions or [],
        },
        headers={"X-CSRF-Token": csrf},
    )


def test_partial_spare_multiple_shipments_and_cancel_reverse(identity_engine: Engine) -> None:
    identity, client, csrf, customer, order = _order_with_inventory(
        identity_engine, "SHIP-FLOW", "1000"
    )
    first = _draft(client, csrf, customer["id"], order["id"], "500", "10")
    assert first.status_code == 201, first.text
    assert first.json()["document_number"].startswith("SHP-202608-")
    confirmed_first = _confirm(client, csrf, first.json())
    assert confirmed_first.status_code == 200, confirmed_first.text
    assert client.get("/api/v1/inventory").json()["items"][0]["available_quantity"] == "490.0000"

    second = _draft(client, csrf, customer["id"], order["id"], "300")
    confirmed_second = _confirm(client, csrf, second.json())
    assert confirmed_second.status_code == 200
    assert client.get("/api/v1/inventory").json()["items"][0]["available_quantity"] == "190.0000"
    cancelled = client.post(
        f"/api/v1/shipments/{second.json()['id']}/cancel",
        json={
            "expected_version": confirmed_second.json()["version"],
            "idempotency_key": str(uuid4()),
            "reason": "客戶取消第二批虛構出貨",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert cancelled.status_code == 200
    assert client.get("/api/v1/inventory").json()["items"][0]["available_quantity"] == "490.0000"
    with Session(identity_engine) as session:
        events = session.scalars(
            select(InventoryLedgerEntry.event_type).where(
                InventoryLedgerEntry.organization_id == identity.organization_id
            )
        ).all()
        assert events.count("shipment_delivered") == 2
        assert events.count("shipment_spare") == 1
        assert events.count("shipment_reversal_delivered") == 1


def test_insufficient_rejects_and_atomic_completion_then_cancel_keeps_completion(
    identity_engine: Engine,
) -> None:
    identity, client, csrf, customer, order = _order_with_inventory(
        identity_engine, "SHIP-COMPLETE", "50"
    )
    draft = _draft(client, csrf, customer["id"], order["id"], "80", "10").json()
    rejected = _confirm(client, csrf, draft)
    assert rejected.status_code == 409
    completed = _confirm(
        client,
        csrf,
        draft,
        completions=[
            {
                "work_order_id": order["id"],
                "quantity": "50",
                "reason": "現場已完成第二批 50 件",
            }
        ],
    )
    assert completed.status_code == 200, completed.text
    assert client.get("/api/v1/inventory").json()["items"][0]["available_quantity"] == "10.0000"
    cancelled = client.post(
        f"/api/v1/shipments/{draft['id']}/cancel",
        json={
            "expected_version": completed.json()["version"],
            "idempotency_key": str(uuid4()),
            "reason": "取消虛構出貨但保留真實完工",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert cancelled.status_code == 200
    assert client.get("/api/v1/inventory").json()["items"][0]["available_quantity"] == "100.0000"
    with Session(identity_engine) as session:
        shipment_completions = session.scalar(
            select(func.count())
            .select_from(FinalCompletionEntry)
            .where(
                FinalCompletionEntry.organization_id == identity.organization_id,
                FinalCompletionEntry.source_type == "shipment_completion",
            )
        )
        assert shipment_completions == 1


def test_confirmation_idempotency_scope_and_confirmed_items_immutable(
    identity_engine: Engine,
) -> None:
    identity, client, csrf, customer, order = _order_with_inventory(
        identity_engine, "SHIP-SAFE", "100"
    )
    draft = _draft(client, csrf, customer["id"], order["id"], "40").json()
    key = uuid4()
    first = _confirm(client, csrf, draft, key=key)
    repeated = _confirm(client, csrf, draft, key=key)
    assert first.status_code == repeated.status_code == 200
    assert first.json()["id"] == repeated.json()["id"]
    _other_identity, other_client, _other_csrf, _customer, _order = _order_with_inventory(
        identity_engine, "SHIP-OTHER", "1"
    )
    assert other_client.get(f"/api/v1/shipments/{draft['id']}").status_code == 404
    with Session(identity_engine) as session:
        item = session.scalar(select(ShipmentItem).where(ShipmentItem.shipment_id == draft["id"]))
        item.delivered_quantity = Decimal("39")
        with pytest.raises(DBAPIError):
            session.commit()
        session.rollback()
        assert (
            session.scalar(
                select(func.count())
                .select_from(Shipment)
                .where(Shipment.organization_id == identity.organization_id)
            )
            == 1
        )
