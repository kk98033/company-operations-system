"""Server-generated request ID contract."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.testclient import TestClient

from app.core.request_context import (
    REQUEST_ID_HEADER,
    current_request_id,
    require_request_id,
)
from app.main import create_app
from tests.settings_factory import make_test_settings


def _client() -> TestClient:
    app = create_app(settings=make_test_settings(), readiness_checks=[])

    @app.get("/_test/request-id")
    def request_id_probe(
        request: Request,
        request_id: Annotated[UUID, Depends(require_request_id)],
    ) -> dict[str, str]:
        assert request.state.request_id == request_id
        assert current_request_id() == request_id
        return {"request_id": str(request_id)}

    @app.get("/_test/unexpected")
    def unexpected_error() -> None:
        raise RuntimeError("synthetic secret must not appear")

    return TestClient(app, raise_server_exceptions=False)


def test_server_generates_fresh_request_id_and_ignores_incoming_header() -> None:
    client = _client()
    forged = "00000000-0000-4000-8000-000000000001"

    first = client.get("/_test/request-id", headers={REQUEST_ID_HEADER: forged})
    second = client.get("/_test/request-id")

    first_id = UUID(first.headers[REQUEST_ID_HEADER])
    second_id = UUID(second.headers[REQUEST_ID_HEADER])
    assert first.status_code == second.status_code == 200
    assert first.json()["request_id"] == str(first_id)
    assert second.json()["request_id"] == str(second_id)
    assert first_id != second_id
    assert str(first_id) != forged
    assert current_request_id() is None


def test_unexpected_error_log_and_response_share_safe_request_id(
    caplog,
) -> None:
    client = _client()

    with caplog.at_level(logging.ERROR, logger="app.core.errors"):
        response = client.get("/_test/unexpected")

    request_id = UUID(response.headers[REQUEST_ID_HEADER])
    record = next(item for item in caplog.records if item.message == "Unhandled API error")
    assert response.status_code == 500
    assert record.request_id == str(request_id)
    assert record.exception_type == "RuntimeError"
    assert "synthetic secret" not in caplog.text
    assert "synthetic secret" not in response.text
