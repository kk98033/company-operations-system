"""PostgreSQL acceptance for persisted PDF generation and download."""

import hashlib
import os

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.modules.document_exports.models import DocumentExport
from tests.integration.test_billing_api import _confirmed_pricing, _issue, _statement
from tests.integration.test_pricing_api import _confirmed_shipment
from tests.integration.test_quotations_api import _payload, _setup

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1", reason="requires isolated PostgreSQL"
    ),
]


def _export(client, csrf: str, kind: str, document_id: str):
    response = client.post(
        f"/api/v1/document-exports/{kind}/{document_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    metadata = response.json()
    download = client.get(metadata["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].endswith('.pdf"')
    assert download.content.startswith(b"%PDF-")
    assert hashlib.sha256(download.content).hexdigest() == metadata["sha256"]
    assert download.headers["x-content-sha256"] == metadata["sha256"]
    assert len(download.content) == metadata["byte_size"]
    return metadata


def test_pdf_exports_cover_reference_templates_and_reuse_exact_version(
    identity_engine: Engine,
) -> None:
    _identity, quote_client, quote_csrf, customer = _setup(identity_engine, "PDF-Q")
    quote = quote_client.post(
        "/api/v1/quotations",
        json=_payload(customer["id"]),
        headers={"X-CSRF-Token": quote_csrf},
    ).json()
    quote_export = _export(quote_client, quote_csrf, "quotation", quote["id"])
    repeated = quote_client.post(
        f"/api/v1/document-exports/quotation/{quote['id']}",
        headers={"X-CSRF-Token": quote_csrf},
    ).json()
    assert repeated["id"] == quote_export["id"]

    _identity, flow_client, flow_csrf, _customer, order, shipment = _confirmed_shipment(
        identity_engine, "PDF-FLOW"
    )
    _export(flow_client, flow_csrf, "work_order", order["id"])
    _export(flow_client, flow_csrf, "shipment", shipment["id"])

    _identity, billing_client, billing_csrf, _customer, pricing = _confirmed_pricing(
        identity_engine, "PDF-BILL"
    )
    statement = _issue(
        billing_client, billing_csrf, _statement(billing_client, billing_csrf, pricing)
    )
    _export(billing_client, billing_csrf, "statement", statement["id"])
    with Session(identity_engine) as session:
        assert session.scalar(select(func.count()).select_from(DocumentExport)) == 4


def test_pdf_download_is_company_scoped(identity_engine: Engine) -> None:
    _identity, client, csrf, customer = _setup(identity_engine, "PDF-A")
    quote = client.post(
        "/api/v1/quotations",
        json=_payload(customer["id"]),
        headers={"X-CSRF-Token": csrf},
    ).json()
    metadata = _export(client, csrf, "quotation", quote["id"])
    _other, other_client, _other_csrf, _other_customer = _setup(identity_engine, "PDF-B")
    assert other_client.get(metadata["download_url"]).status_code == 404
