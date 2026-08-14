"""PostgreSQL acceptance for Phase 9 operational read models and CSV."""

import csv
import io
import os
from time import perf_counter
from uuid import uuid4

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from tests.integration.test_quotations_api import _payload, _setup

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1", reason="requires isolated PostgreSQL"
    ),
]


def test_search_customer_overview_and_csv_are_company_scoped(identity_engine: Engine) -> None:
    _identity, client, csrf, customer = _setup(identity_engine, "OPS-A")
    quote = client.post(
        "/api/v1/quotations",
        json=_payload(customer["id"]),
        headers={"X-CSRF-Token": csrf},
    )
    assert quote.status_code == 201
    _other, other_client, _other_csrf, _other_customer = _setup(identity_engine, "OPS-B")

    search = client.get("/api/v1/operations/search", params={"keyword": "OPS-A"})
    assert search.status_code == 200
    assert {item["entity_type"] for item in search.json()["items"]} == {
        "customer",
        "quotation",
    }
    assert all("OPS-B" not in str(item) for item in search.json()["items"])
    other_search = other_client.get("/api/v1/operations/search", params={"keyword": "OPS-A"})
    assert other_search.status_code == 200
    assert other_search.json()["items"] == []

    overview = client.get(f"/api/v1/operations/customers/{customer['id']}")
    assert overview.status_code == 200
    assert overview.json()["counts"] == {"quotation": 1}
    assert other_client.get(f"/api/v1/operations/customers/{customer['id']}").status_code == 404

    formula_customer = client.post(
        "/api/v1/customers",
        json={"code": "FORMULA", "name": "=2+2"},
        headers={"X-CSRF-Token": csrf},
    )
    assert formula_customer.status_code == 201
    exported = client.get("/api/v1/operations/exports/customers.csv")
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
    formula_row = next(row for row in rows if row[0] == "FORMULA")
    assert formula_row[1] == "'=2+2"


def test_dashboard_only_returns_authorized_cards(identity_engine: Engine) -> None:
    _identity, client, _csrf, _customer = _setup(identity_engine, "OPS-DASH")
    response = client.get("/api/v1/operations/dashboard", params={"as_of": "2026-08-15"})
    assert response.status_code == 200
    assert response.json()["cards"] == []


def test_search_has_bounded_queries_and_response_time(identity_engine: Engine) -> None:
    identity, client, _csrf, _customer = _setup(identity_engine, "PERF")
    with Session(identity_engine) as session, session.begin():
        session.add_all(
            Customer(
                id=uuid4(),
                organization_id=identity.organization_id,
                code=f"PERF-{index:04d}",
                name=f"虛構效能客戶 {index:04d}",
            )
            for index in range(300)
        )
    statements = 0

    def count_statement(*_args) -> None:
        nonlocal statements
        statements += 1

    event.listen(identity_engine, "before_cursor_execute", count_statement)
    started = perf_counter()
    try:
        response = client.get(
            "/api/v1/operations/search",
            params={"keyword": "PERF-0299", "limit": 20},
        )
    finally:
        elapsed = perf_counter() - started
        event.remove(identity_engine, "before_cursor_execute", count_statement)
    assert response.status_code == 200
    assert response.json()["items"][0]["primary_text"].startswith("PERF-0299")
    assert statements <= 5
    assert elapsed < 2.0
