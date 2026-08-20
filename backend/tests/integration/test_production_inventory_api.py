"""PostgreSQL acceptance for Phase 5 production and inventory rules."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.modules.customers.models import CustomerWorkItem
from app.modules.production.models import (
    FinalCompletionEntry,
    InventoryAdjustment,
    InventoryLedgerEntry,
    ProcessEvent,
)
from tests.integration.auth_test_support import create_auth_member, make_auth_client
from tests.integration.work_order_test_support import grant, setup_company, work_order_payload

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _confirmed_order(engine: Engine, suffix: str):
    identity, client, csrf, customer = setup_company(engine, suffix)
    created = client.post(
        "/api/v1/work-orders",
        json=work_order_payload(customer["id"]),
        headers={"X-CSRF-Token": csrf},
    ).json()
    response = client.post(
        f"/api/v1/work-orders/{created['id']}/confirm",
        json={"expected_updated_at": created["updated_at"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    return identity, client, csrf, response.json()


def _event(client, csrf: str, order_id: str, event_type: str, *, key=None):
    return client.post(
        f"/api/v1/production/work-orders/{order_id}/process-events",
        json={
            "process_code": "transport",
            "event_type": event_type,
            "idempotency_key": str(key or uuid4()),
            **({"reason": "重新安排運送"} if event_type == "reopen" else {}),
        },
        headers={"X-CSRF-Token": csrf},
    )


def _completion(client, csrf: str, order_id: str, quantity: str, *, key=None):
    return client.post(
        f"/api/v1/production/work-orders/{order_id}/final-completions",
        json={
            "quantity": quantity,
            "reason": "實際完工核定",
            "idempotency_key": str(key or uuid4()),
        },
        headers={"X-CSRF-Token": csrf},
    )


def test_transport_gate_partial_completion_reversal_and_adjustment(identity_engine: Engine) -> None:
    identity, client, csrf, order = _confirmed_order(identity_engine, "PROD-FLOW")
    order_id = order["id"]
    assert client.get("/api/v1/production").json()["items"][0]["available_quantity"] == "0"
    assert _completion(client, csrf, order_id, "600").status_code == 409

    assert _event(client, csrf, order_id, "start").status_code == 201
    assert _event(client, csrf, order_id, "complete").status_code == 201
    assert (
        client.get(f"/api/v1/production/work-orders/{order_id}").json()["order"][
            "available_quantity"
        ]
        == "0"
    )

    key = uuid4()
    first = _completion(client, csrf, order_id, "600", key=key)
    assert first.status_code == 201, first.text
    assert first.json()["available_quantity"] == "600.0000"
    repeated = _completion(client, csrf, order_id, "600", key=key)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    second = _completion(client, csrf, order_id, "400")
    assert second.status_code == 201
    assert second.json()["available_quantity"] == "1000.0000"

    inventory = client.get("/api/v1/inventory").json()
    assert inventory["items"][0]["available_quantity"] == "1000.0000"
    adjustment = client.post(
        f"/api/v1/inventory/{order_id}/adjustments",
        json={"quantity": "-5", "reason": "盤點減少", "idempotency_key": str(uuid4())},
        headers={"X-CSRF-Token": csrf},
    )
    assert adjustment.status_code == 201
    assert (
        client.post(
            f"/api/v1/inventory/{order_id}/adjustments",
            json={"quantity": "-1000", "reason": "不可負庫存", "idempotency_key": str(uuid4())},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )

    reversed_second = client.post(
        f"/api/v1/production/final-completions/{second.json()['id']}/reverse",
        json={"reason": "第二批完工資料誤植", "idempotency_key": str(uuid4())},
        headers={"X-CSRF-Token": csrf},
    )
    assert reversed_second.status_code == 201
    assert reversed_second.json()["available_quantity"] == "595.0000"
    assert (
        client.post(
            f"/api/v1/production/final-completions/{first.json()['id']}/reverse",
            json={"reason": "將導致負庫存", "idempotency_key": str(uuid4())},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )

    assert _event(client, csrf, order_id, "reopen").status_code == 201
    assert _completion(client, csrf, order_id, "10").status_code == 409
    assert _event(client, csrf, order_id, "complete").status_code == 201
    assert _completion(client, csrf, order_id, "10").status_code == 201

    with Session(identity_engine) as session:
        work_item = session.scalar(
            select(CustomerWorkItem).where(
                CustomerWorkItem.organization_id == identity.organization_id,
                CustomerWorkItem.source_reference == order_id,
            )
        )
        assert work_item is not None
        assert work_item.name == "虛構彩盒"


def test_phase5_rows_are_append_only_and_company_scoped(identity_engine: Engine) -> None:
    identity_a, client_a, csrf_a, order_a = _confirmed_order(identity_engine, "PROD-A")
    _identity_b, client_b, _csrf_b, _order_b = _confirmed_order(identity_engine, "PROD-B")
    start = _event(client_a, csrf_a, order_a["id"], "start")
    assert start.status_code == 201
    assert client_b.get(f"/api/v1/production/work-orders/{order_a['id']}").status_code == 404

    with Session(identity_engine) as session:
        row = session.get(ProcessEvent, start.json()["id"])
        assert row is not None
        row.reason = "不可覆寫"
        with pytest.raises(DBAPIError):
            session.commit()
        session.rollback()

    with Session(identity_engine) as session:
        assert session.scalar(select(InventoryLedgerEntry)) is None

    with Session(identity_engine) as session:
        invalid_completion = FinalCompletionEntry(
            organization_id=identity_a.organization_id,
            work_order_id=order_a["id"],
            entry_type="completion",
            source_type="manual",
            quantity=Decimal("1"),
            transport_process_event_id=start.json()["id"],
            reversal_of_id=None,
            correlation_id=uuid4(),
            idempotency_key=uuid4(),
            reason="尚未完成運送",
            actor_membership_id=identity_a.membership_id,
            actor_user_id=identity_a.user_id,
            occurred_at=datetime.now(UTC),
        )
        session.add(invalid_completion)
        with pytest.raises(DBAPIError):
            session.commit()
        session.rollback()

    with Session(identity_engine) as session:
        adjustment = InventoryAdjustment(
            organization_id=identity_a.organization_id,
            work_order_id=order_a["id"],
            quantity=Decimal("-1"),
            reason="直接寫入不得繞過負庫存保護",
            idempotency_key=uuid4(),
            approved_by_membership_id=identity_a.membership_id,
            approved_by_user_id=identity_a.user_id,
            occurred_at=datetime.now(UTC),
        )
        session.add(adjustment)
        session.flush()
        session.add(
            InventoryLedgerEntry(
                organization_id=identity_a.organization_id,
                work_order_id=order_a["id"],
                event_type="manual_adjustment",
                quantity=Decimal("-1"),
                final_completion_entry_id=None,
                inventory_adjustment_id=adjustment.id,
                reason=adjustment.reason,
                occurred_at=adjustment.occurred_at,
            )
        )
        with pytest.raises(DBAPIError):
            session.commit()


def test_concurrent_duplicate_completion_is_single_inventory_entry(
    identity_engine: Engine,
) -> None:
    identity, first_client, first_csrf, order = _confirmed_order(identity_engine, "PROD-IDEMPOTENT")
    order_id = order["id"]
    assert _event(first_client, first_csrf, order_id, "start").status_code == 201
    assert _event(first_client, first_csrf, order_id, "complete").status_code == 201

    second_identity = create_auth_member(
        identity_engine,
        organization_id=identity.organization_id,
        password=SecretStr(f"Synthetic-SECOND-{uuid4()}"),
    )
    grant(identity_engine, second_identity, "production.complete")
    second_client = make_auth_client(identity_engine)
    login = second_client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(second_identity.organization_id),
            "login_name": second_identity.login_name,
            "password": second_identity.password.get_secret_value(),
        },
    )
    assert login.status_code == 200
    second_csrf = second_client.cookies.get("company_system_csrf")
    idempotency_key = uuid4()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda request: _completion(*request, key=idempotency_key),
                [
                    (first_client, first_csrf, order_id, "50"),
                    (second_client, second_csrf, order_id, "50"),
                ],
            )
        )
    assert [response.status_code for response in responses] == [201, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    with Session(identity_engine) as session:
        rows = session.scalars(
            select(InventoryLedgerEntry).where(
                InventoryLedgerEntry.work_order_id == order_id,
                InventoryLedgerEntry.event_type == "final_completion",
            )
        ).all()
        assert [str(row.quantity) for row in rows].count("50.0000") == 1
