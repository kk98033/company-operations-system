"""Structured access-log privacy and correlation contract."""

import json
import logging
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.testclient import TestClient

from app.core.access_logging import AccessActor, attach_access_actor
from app.core.request_context import REQUEST_ID_HEADER
from app.main import create_app
from tests.settings_factory import make_test_settings


def _access_records(caplog) -> list[dict[str, object]]:
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.access"
    ]


def _test_app():
    app = create_app(settings=make_test_settings(), readiness_checks=[])

    @app.get("/_test/resources/{resource_id}")
    def resource(resource_id: UUID, request: Request) -> dict[str, str]:
        actor = AccessActor(
            organization_id=uuid4(),
            user_id=uuid4(),
            organization_member_id=uuid4(),
            session_id=uuid4(),
        )
        attach_access_actor(request, actor=actor)
        request.state.test_actor = actor
        return {"id": str(resource_id)}

    @app.get("/_test/failure")
    def failure() -> None:
        raise RuntimeError("access-log-secret-must-not-appear")

    return app


def test_access_log_uses_route_template_request_id_and_safe_actor(caplog) -> None:
    app = _test_app()
    resource_id = uuid4()

    with caplog.at_level(logging.INFO, logger="app.access"):
        response = TestClient(app).get(
            f"/_test/resources/{resource_id}",
            params={"private": "query-secret-must-not-appear"},
        )

    records = _access_records(caplog)
    assert response.status_code == 200
    assert len(records) == 1
    record = records[0]
    assert record["event"] == "http_access"
    assert record["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert record["method"] == "GET"
    assert record["route"] == "/_test/resources/{resource_id}"
    assert record["status_code"] == 200
    assert record["response_size_bytes"] == len(response.content)
    assert record["error_code"] is None
    assert all(
        record[field] is not None
        for field in (
            "organization_id",
            "user_id",
            "organization_member_id",
            "session_id",
        )
    )
    assert str(resource_id) not in caplog.text
    assert "query-secret-must-not-appear" not in caplog.text


def test_unmatched_and_validation_logs_never_record_path_or_submitted_values(
    caplog,
) -> None:
    app = _test_app()
    client = TestClient(app)

    with caplog.at_level(logging.WARNING, logger="app.access"):
        missing = client.get("/private-path-secret", params={"token": "query-secret"})
        invalid = client.get("/_test/resources/not-a-uuid")

    records = _access_records(caplog)
    assert missing.status_code == 404
    assert invalid.status_code == 422
    assert len(records) == 2
    assert records[0]["route"] == "<unmatched>"
    assert records[0]["error_code"] == "NOT_FOUND"
    assert records[1]["route"] == "/_test/resources/{resource_id}"
    assert records[1]["error_code"] == "VALIDATION_ERROR"
    assert "private-path-secret" not in caplog.text
    assert "query-secret" not in caplog.text
    assert "not-a-uuid" not in caplog.text


def test_unexpected_error_emits_one_safe_error_access_record(caplog) -> None:
    app = _test_app()

    with caplog.at_level(logging.INFO):
        response = TestClient(app, raise_server_exceptions=False).get(
            "/_test/failure"
        )

    records = _access_records(caplog)
    assert response.status_code == 500
    assert len(records) == 1
    assert records[0]["status_code"] == 500
    assert records[0]["error_code"] == "INTERNAL_SERVER_ERROR"
    assert records[0]["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert "access-log-secret-must-not-appear" not in caplog.text


def test_access_record_contains_only_allowlisted_top_level_fields(caplog) -> None:
    app = _test_app()

    with caplog.at_level(logging.INFO, logger="app.access"):
        TestClient(app).get(f"/_test/resources/{uuid4()}")

    [record] = _access_records(caplog)
    assert set(record) == {
        "timestamp",
        "event",
        "request_id",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "response_size_bytes",
        "slow_request",
        "error_code",
        "organization_id",
        "user_id",
        "organization_member_id",
        "session_id",
    }
