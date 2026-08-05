import logging
from typing import Annotated

import pytest
from fastapi import Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError, field_validator

from app.core.errors import ApplicationError
from app.main import create_app
from tests.settings_factory import make_test_settings


def test_unknown_route_uses_error_envelope() -> None:
    client = TestClient(create_app(settings=make_test_settings()))

    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "找不到要求的資源",
            "details": None,
        }
    }


def test_validation_error_uses_error_envelope() -> None:
    app = create_app(settings=make_test_settings())

    @app.get("/_test/validated")
    def validated(limit: int = Query(ge=1)) -> dict[str, int]:
        return {"limit": limit}

    client = TestClient(app)
    response = client.get("/_test/validated", params={"limit": "zero"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "請檢查輸入資料"
    assert body["error"]["details"][0]["loc"] == ["query", "limit"]


@pytest.mark.parametrize(
    ("error_type", "safe_message"),
    [
        ("missing", "此欄位為必填"),
        ("enum", "值不在允許範圍"),
        ("greater_than_equal", "數值超出允許範圍"),
        ("string_too_short", "文字長度不符合限制"),
        ("bool_type", "格式不正確"),
        ("value_error", "輸入資料無效"),
    ],
)
def test_validation_error_types_use_fixed_safe_messages(
    error_type: str,
    safe_message: str,
) -> None:
    secret_canary = "pydantic-error-secret-canary"
    app = create_app(settings=make_test_settings())

    @app.get(f"/_test/error-type/{error_type}")
    def fail_validation() -> None:
        raise RequestValidationError(
            [
                {
                    "type": error_type,
                    "loc": ("query", "value"),
                    "msg": secret_canary,
                    "input": secret_canary,
                    "ctx": {"reason": secret_canary},
                    "url": f"https://invalid.example/{secret_canary}",
                }
            ]
        )

    response = TestClient(app).get(f"/_test/error-type/{error_type}")

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {
            "loc": ["query", "value"],
            "msg": safe_message,
            "type": error_type,
        }
    ]
    assert secret_canary not in response.text


def test_custom_validation_error_type_is_normalized() -> None:
    secret_canary = "custom-type-secret-canary"
    app = create_app(settings=make_test_settings())

    @app.get("/_test/custom-error-type")
    def fail_validation() -> None:
        raise RequestValidationError(
            [
                {
                    "type": secret_canary,
                    "loc": ("query", "value"),
                    "msg": secret_canary,
                    "input": secret_canary,
                }
            ]
        )

    response = TestClient(app).get("/_test/custom-error-type")

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["type"] == "value_error"
    assert secret_canary not in response.text


def test_expected_application_error_uses_error_envelope() -> None:
    app = create_app(settings=make_test_settings())

    @app.get("/_test/conflict")
    def conflict() -> None:
        raise ApplicationError(
            status_code=409,
            code="VERSION_CONFLICT",
            message="資料已被其他使用者更新",
            details={"expected_version": 1},
        )

    client = TestClient(app)
    response = client.get("/_test/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "VERSION_CONFLICT",
            "message": "資料已被其他使用者更新",
            "details": {"expected_version": 1},
        }
    }


def test_validation_error_does_not_echo_input_or_validator_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_canary = "validation-secret-canary"
    app = create_app(settings=make_test_settings())

    class SecretQuery(BaseModel):
        value: str

        @field_validator("value")
        @classmethod
        def reject_value(cls, value: str) -> str:
            raise ValueError(f"validator rejected {value}")

    def validate_secret_query(value: str = Query()) -> SecretQuery:
        try:
            return SecretQuery(value=value)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from None

    @app.get("/_test/secret-validation")
    def secret_validation(
        _query: Annotated[SecretQuery, Depends(validate_secret_query)],
    ) -> None:
        return None

    with caplog.at_level(logging.ERROR, logger="app.core.errors"):
        response = TestClient(app).get(
            "/_test/secret-validation",
            params={"value": secret_canary},
        )

    assert response.status_code == 422
    assert secret_canary not in response.text
    assert "input" not in response.text
    assert "ctx" not in response.text
    assert "url" not in response.text
    assert secret_canary not in caplog.text


def test_http_exception_does_not_expose_arbitrary_detail() -> None:
    secret_canary = "http-detail-secret-canary"
    app = create_app(settings=make_test_settings())

    @app.get("/_test/http-error")
    def http_error() -> None:
        raise HTTPException(
            status_code=400,
            detail=secret_canary,
            headers={
                "Retry-After": "15",
                "X-Internal-Secret": secret_canary,
            },
        )

    response = TestClient(app).get("/_test/http-error")

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "BAD_REQUEST",
        "message": "請求格式錯誤",
        "details": None,
    }
    assert response.headers["retry-after"] == "15"
    assert "x-internal-secret" not in response.headers
    assert secret_canary not in response.text


def test_method_not_allowed_preserves_only_safe_protocol_header() -> None:
    client = TestClient(create_app(settings=make_test_settings()))

    response = client.post("/api/v1/health/live")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.json()["error"] == {
        "code": "METHOD_NOT_ALLOWED",
        "message": "不允許使用此 HTTP method",
        "details": None,
    }


def test_unauthorized_preserves_authentication_challenge() -> None:
    app = create_app(settings=make_test_settings())

    @app.get("/_test/unauthorized")
    def unauthorized() -> None:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="company-system"'},
        )

    response = TestClient(app).get("/_test/unauthorized")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == (
        'Bearer realm="company-system"'
    )
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_unexpected_error_does_not_expose_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(settings=make_test_settings())

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("database password must not leak")

    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="app.core.errors"):
        response = client.get("/_test/crash")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "伺服器發生未預期錯誤",
            "details": None,
        }
    }
    assert "database password" not in response.text
    assert "database password" not in caplog.text
    assert any(
        getattr(record, "exception_type", None) == "RuntimeError"
        for record in caplog.records
    )
