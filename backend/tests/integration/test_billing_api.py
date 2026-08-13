"""PostgreSQL acceptance for Phase 8 statements and receipts."""

import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.modules.billing.models import Receipt, ReceiptAllocation, StatementItem
from tests.integration.test_pricing_api import _confirmed_shipment, _create_pricing

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1", reason="requires isolated PostgreSQL"
    ),
]


def _confirmed_pricing(engine: Engine, suffix: str):
    identity, client, csrf, customer, _order, shipment = _confirmed_shipment(engine, suffix)
    draft = _create_pricing(client, csrf, shipment["items"][0]["id"]).json()
    response = client.post(
        f"/api/v1/pricing-documents/{draft['id']}/confirm",
        json={
            "expected_version": draft["version"],
            "idempotency_key": str(uuid4()),
            "update_default_line_numbers": [],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    return identity, client, csrf, customer, response.json()


def _statement(client, csrf: str, pricing: dict, tax: bool = False):
    item = pricing["items"][0]
    payload = {
        "statement_date": "2026-08-13",
        "period_from": "2026-08-01",
        "period_to": "2026-08-31",
        "pricing_item_ids": [item["id"]],
        "tax_enabled": tax,
        "tax_rate_percent": "5" if tax else None,
        "rounding_scope": "grand_total" if tax else None,
        "rounding_decimal_places": 0 if tax else None,
        "notes": "虛構對帳",
        "idempotency_key": str(uuid4()),
    }
    response = client.post("/api/v1/statements", json=payload, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201, response.text
    return response.json()


def _issue(client, csrf: str, row: dict):
    response = client.post(
        f"/api/v1/statements/{row['id']}/issue",
        json={"expected_version": row["version"], "idempotency_key": str(uuid4())},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_unique_statement_source_tax_snapshot_and_pricing_cancel_block(
    identity_engine: Engine,
) -> None:
    _identity, client, csrf, _customer, pricing = _confirmed_pricing(identity_engine, "BILL-STMT")
    row = _statement(client, csrf, pricing, tax=True)
    assert row["document_number"].startswith("STM-202608-")
    assert row["subtotal_before_rounding"] == "10250.0000"
    assert row["tax_amount"] == "512.5000"
    assert row["grand_total"] == "10763.0000"
    duplicate = client.post(
        "/api/v1/statements",
        json={
            "statement_date": "2026-08-13",
            "period_from": "2026-08-01",
            "period_to": "2026-08-31",
            "pricing_item_ids": [pricing["items"][0]["id"]],
            "tax_enabled": False,
            "notes": None,
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert duplicate.status_code == 409
    issued = _issue(client, csrf, row)
    blocked = client.post(
        f"/api/v1/pricing-documents/{pricing['id']}/cancel",
        json={
            "expected_version": pricing["version"],
            "idempotency_key": str(uuid4()),
            "reason": "已對帳不可取消",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert issued["status"] == "issued"
    assert blocked.status_code == 409


def test_partial_receipt_tail_payment_and_reversal_restore_balance(identity_engine: Engine) -> None:
    _identity, client, csrf, customer, pricing = _confirmed_pricing(identity_engine, "BILL-RECEIPT")
    issued = _issue(client, csrf, _statement(client, csrf, pricing))
    first = client.post(
        "/api/v1/receipts",
        json={
            "receipt_date": "2026-08-13",
            "customer_id": customer["id"],
            "payment_method": "轉帳",
            "reference_number": "SYN-1",
            "amount": "4000",
            "allocations": [{"statement_id": issued["id"], "amount": "4000"}],
            "notes": None,
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert first.status_code == 201, first.text
    partial = client.get(f"/api/v1/statements/{issued['id']}").json()
    assert partial["status"] == "partially_paid" and partial["outstanding_amount"] == "6250.0000"
    over = client.post(
        "/api/v1/receipts",
        json={
            "receipt_date": "2026-08-13",
            "customer_id": customer["id"],
            "payment_method": "現金",
            "amount": "7000",
            "allocations": [{"statement_id": issued["id"], "amount": "7000"}],
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert over.status_code == 409
    tail = client.post(
        "/api/v1/receipts",
        json={
            "receipt_date": "2026-08-13",
            "customer_id": customer["id"],
            "payment_method": "現金",
            "amount": "6250",
            "allocations": [{"statement_id": issued["id"], "amount": "6250"}],
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert (
        tail.status_code == 201
        and client.get(f"/api/v1/statements/{issued['id']}").json()["status"] == "paid"
    )
    reversed_row = client.post(
        f"/api/v1/receipts/{tail.json()['id']}/reverse",
        json={"idempotency_key": str(uuid4()), "reason": "虛構退票"},
        headers={"X-CSRF-Token": csrf},
    )
    assert reversed_row.status_code == 200
    restored = client.get(f"/api/v1/statements/{issued['id']}").json()
    assert restored["status"] == "partially_paid" and restored["outstanding_amount"] == "6250.0000"


def test_company_scope_aging_and_cancel_with_payment_blocked(identity_engine: Engine) -> None:
    _identity, client, csrf, customer, pricing = _confirmed_pricing(identity_engine, "BILL-SCOPE")
    issued = _issue(client, csrf, _statement(client, csrf, pricing))
    receipt = client.post(
        "/api/v1/receipts",
        json={
            "receipt_date": "2026-08-13",
            "customer_id": customer["id"],
            "payment_method": "轉帳",
            "amount": "100",
            "allocations": [{"statement_id": issued["id"], "amount": "100"}],
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert receipt.status_code == 201
    blocked = client.post(
        f"/api/v1/statements/{issued['id']}/cancel",
        json={
            "expected_version": issued["version"] + 1,
            "idempotency_key": str(uuid4()),
            "reason": "有收款不可取消",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert blocked.status_code == 409
    aging = client.get("/api/v1/receivables/aging", params={"as_of": "2026-09-20"}).json()
    assert aging[0]["days_31_60"] == "10150.0000"
    _other, other_client, *_ = _confirmed_pricing(identity_engine, "BILL-OTHER")
    assert other_client.get(f"/api/v1/statements/{issued['id']}").status_code == 404


def test_database_rejects_overallocation_and_billing_ledger_mutation(
    identity_engine: Engine,
) -> None:
    identity, client, csrf, customer, pricing = _confirmed_pricing(identity_engine, "BILL-DB")
    issued = _issue(client, csrf, _statement(client, csrf, pricing))
    receipt = client.post(
        "/api/v1/receipts",
        json={
            "receipt_date": "2026-08-13",
            "customer_id": customer["id"],
            "payment_method": "轉帳",
            "amount": "100",
            "allocations": [{"statement_id": issued["id"], "amount": "100"}],
            "idempotency_key": str(uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    ).json()
    with Session(identity_engine) as session:
        oversized_receipt = Receipt(
            organization_id=identity.organization_id,
            document_number=f"RCT-DB-{uuid4().hex[:8]}",
            receipt_date=date(2026, 8, 13),
            customer_id=customer["id"],
            customer_snapshot={"name": customer["name"]},
            payment_method="轉帳",
            amount="20000",
            status="confirmed",
            idempotency_key=uuid4(),
            created_by_membership_id=identity.membership_id,
            created_by_user_id=identity.user_id,
            confirmed_at=datetime.now(UTC),
        )
        session.add(oversized_receipt)
        session.flush()
        session.add(
            ReceiptAllocation(
                organization_id=identity.organization_id,
                receipt_id=oversized_receipt.id,
                statement_id=issued["id"],
                amount="20000",
            )
        )
        with pytest.raises(DBAPIError, match="exceeds statement balance"):
            session.flush()
        session.rollback()
    with Session(identity_engine) as session:
        with pytest.raises(DBAPIError, match="receipt allocations are immutable"):
            session.execute(
                update(ReceiptAllocation)
                .where(ReceiptAllocation.receipt_id == receipt["id"])
                .values(amount="101")
            )
        session.rollback()
        item_id = issued["items"][0]["id"]
        with pytest.raises(DBAPIError, match="statement items are immutable"):
            session.execute(
                update(StatementItem).where(StatementItem.id == item_id).values(amount="1")
            )
