from fastapi import Query
from fastapi.testclient import TestClient

from app.core.errors import ApplicationError
from app.main import create_app


def test_unknown_route_uses_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Not Found",
            "details": None,
        }
    }


def test_validation_error_uses_error_envelope() -> None:
    app = create_app()

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


def test_expected_application_error_uses_error_envelope() -> None:
    app = create_app()

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


def test_unexpected_error_does_not_expose_exception() -> None:
    app = create_app()

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("database password must not leak")

    client = TestClient(app, raise_server_exceptions=False)
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
