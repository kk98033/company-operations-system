from fastapi.testclient import TestClient

from app.core.readiness import ReadinessCheckResult
from app.main import create_app


def test_live_reports_alive_without_dependency_checks() -> None:
    def exploding_check() -> ReadinessCheckResult:
        raise RuntimeError("must not run from live")

    client = TestClient(create_app(readiness_checks=[exploding_check]))

    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "company-system-api",
    }


def test_default_ready_explicitly_reports_database_not_configured() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "SERVICE_NOT_READY",
            "message": "必要相依服務尚未就緒",
            "details": {
                "checks": [
                    {
                        "name": "database",
                        "status": "not_configured",
                        "message": "資料庫就緒檢查將在 Slice 0.5 建立",
                    }
                ]
            },
        }
    }


def test_ready_reports_success_when_injected_checks_pass() -> None:
    def database_ok() -> ReadinessCheckResult:
        return ReadinessCheckResult(name="database", status="ok")

    client = TestClient(create_app(readiness_checks=[database_ok]))

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": [{"name": "database", "status": "ok", "message": None}],
    }


def test_ready_converts_check_exception_to_safe_failure() -> None:
    def database_check() -> ReadinessCheckResult:
        raise RuntimeError("postgres password must not leak")

    client = TestClient(create_app(readiness_checks=[database_check]))

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SERVICE_NOT_READY"
    assert body["error"]["details"]["checks"] == [
        {
            "name": "database_check",
            "status": "error",
            "message": "檢查執行失敗",
        }
    ]
    assert "postgres password" not in response.text
