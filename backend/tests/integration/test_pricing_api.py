"""PostgreSQL acceptance for Phase 7 pricing and price memory."""

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.modules.pricing.models import PriceHistory, PricingDocument, PricingItem
from tests.integration.test_shipments_api import _confirm, _draft, _order_with_inventory

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1", reason="requires isolated PostgreSQL"
    ),
]


def _confirmed_shipment(engine: Engine, suffix: str):
    identity, client, csrf, customer, order = _order_with_inventory(engine, suffix, "1000")
    draft = _draft(client, csrf, customer["id"], order["id"], "500", "10").json()
    shipment = _confirm(client, csrf, draft).json()
    return identity, client, csrf, customer, order, shipment


def _create_pricing(client, csrf: str, shipment_item_id: str):
    return client.post(
        "/api/v1/pricing-documents",
        json={
            "pricing_date": "2026-08-13",
            "shipment_item_ids": [shipment_item_id],
            "notes": "虛構計價測試",
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )


def test_base_pricing_excludes_spare_and_prevents_duplicate(identity_engine: Engine) -> None:
    _identity, client, csrf, _customer, _order, shipment = _confirmed_shipment(
        identity_engine, "PRICE-BASE"
    )
    source_id = shipment["items"][0]["id"]
    pending = client.get("/api/v1/pricing-documents/pending-items").json()["items"][0]
    assert pending["pricing_status"] == "pending"
    created = _create_pricing(client, csrf, source_id)
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["document_number"].startswith("PRC-20260813-")
    assert row["items"][0]["item_type"] == "base"
    assert row["items"][0]["quantity"] == "500.0000"
    assert row["items"][0]["unit_price"] == "20.5000"
    assert row["items"][0]["subtotal"] == "10250.0000"
    assert all(item["item_type"] != "spare" for item in row["items"])
    duplicate = _create_pricing(client, csrf, source_id)
    assert duplicate.status_code == 409
    pending = client.get("/api/v1/pricing-documents/pending-items").json()["items"][0]
    assert pending["pricing_status"] == "pricing"


def test_explicit_spare_manual_fee_confirm_memory_cancel_and_reopen(
    identity_engine: Engine,
) -> None:
    _identity, client, csrf, _customer, _order, shipment = _confirmed_shipment(
        identity_engine, "PRICE-LIFE"
    )
    source = shipment["items"][0]
    created = _create_pricing(client, csrf, source["id"]).json()
    updated = client.put(
        f"/api/v1/pricing-documents/{created['id']}",
        json={
            "pricing_date": "2026-08-13",
            "notes": "明確收取部分備品與版費",
            "expected_version": created["version"],
            "items": [
                {
                    "source_shipment_item_id": source["id"],
                    "item_type": "base",
                    "content": "虛構彩盒正式出貨",
                    "product_name": "虛構彩盒",
                    "specification": "100 x 120 x 30 mm",
                    "quantity": "500",
                    "unit_price": "20.50",
                    "plate_fee": "0",
                    "die_fee": "0",
                },
                {
                    "source_shipment_item_id": source["id"],
                    "item_type": "spare",
                    "content": "明確可請款備品",
                    "product_name": "虛構彩盒",
                    "specification": "100 x 120 x 30 mm",
                    "quantity": "5",
                    "unit_price": "20.50",
                    "plate_fee": "0",
                    "die_fee": "0",
                },
                {
                    "source_shipment_item_id": None,
                    "item_type": "manual",
                    "content": "追加版費",
                    "product_name": "虛構彩盒",
                    "specification": "100 x 120 x 30 mm",
                    "quantity": "0",
                    "unit_price": "0",
                    "plate_fee": "7000",
                    "die_fee": "0",
                },
            ],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["total_amount"] == "17352.5000"
    key = str(uuid4())
    confirmed = client.post(
        f"/api/v1/pricing-documents/{created['id']}/confirm",
        json={
            "expected_version": updated.json()["version"],
            "idempotency_key": key,
            "update_default_line_numbers": [1],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert confirmed.status_code == 200, confirmed.text
    repeated = client.post(
        f"/api/v1/pricing-documents/{created['id']}/confirm",
        json={
            "expected_version": updated.json()["version"],
            "idempotency_key": key,
            "update_default_line_numbers": [1],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert repeated.status_code == 200
    suggestions = client.get(
        "/api/v1/price-suggestions",
        params={"customer_id": created["customer_id"], "product_name": "虛構彩盒"},
    ).json()["items"]
    assert suggestions[0]["is_default"] is True
    assert suggestions[0]["unit_price"] == "20.5000"
    blocked = client.post(
        f"/api/v1/shipments/{shipment['id']}/cancel",
        json={
            "expected_version": shipment["version"],
            "idempotency_key": str(uuid4()),
            "reason": "有有效計價時禁止",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert blocked.status_code == 409
    cancelled = client.post(
        f"/api/v1/pricing-documents/{created['id']}/cancel",
        json={
            "expected_version": confirmed.json()["version"],
            "idempotency_key": str(uuid4()),
            "reason": "虛構取消",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert cancelled.status_code == 200
    reopened = client.post(
        f"/api/v1/pricing-documents/{created['id']}/reopen",
        json={"expected_version": cancelled.json()["version"], "idempotency_key": str(uuid4())},
        headers={"X-CSRF-Token": csrf},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "draft"


def test_scope_and_confirmed_items_immutable(identity_engine: Engine) -> None:
    identity, client, csrf, _customer, _order, shipment = _confirmed_shipment(
        identity_engine, "PRICE-SAFE"
    )
    created = _create_pricing(client, csrf, shipment["items"][0]["id"]).json()
    confirmed = client.post(
        f"/api/v1/pricing-documents/{created['id']}/confirm",
        json={
            "expected_version": created["version"],
            "idempotency_key": str(uuid4()),
            "update_default_line_numbers": [],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert confirmed.status_code == 200
    _other, other_client, _other_csrf, *_rest = _confirmed_shipment(identity_engine, "PRICE-OTHER")
    assert other_client.get(f"/api/v1/pricing-documents/{created['id']}").status_code == 404
    with Session(identity_engine) as session:
        item = session.scalar(
            select(PricingItem).where(PricingItem.pricing_document_id == created["id"])
        )
        item.unit_price = Decimal("1")
        with pytest.raises(DBAPIError):
            session.commit()
        session.rollback()
        assert (
            session.scalar(
                select(func.count())
                .select_from(PriceHistory)
                .where(PriceHistory.organization_id == identity.organization_id)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(PricingDocument)
                .where(PricingDocument.organization_id == identity.organization_id)
            )
            == 1
        )
