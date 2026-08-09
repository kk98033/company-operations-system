from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app
from tests.settings_factory import make_test_settings, valid_settings_values


def test_development_openapi_has_stable_health_and_error_contracts() -> None:
    client = TestClient(create_app(settings=make_test_settings()))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "公司管理系統 API"
    assert schema["info"]["version"] == "0.1.0"
    live = schema["paths"]["/api/v1/health/live"]["get"]
    ready = schema["paths"]["/api/v1/health/ready"]["get"]
    assert live["operationId"] == "health_live"
    assert ready["operationId"] == "health_ready"
    assert ready["responses"]["503"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ErrorResponse"}

    for operation in (live, ready):
        for status_code in (
            "400",
            "401",
            "403",
            "404",
            "405",
            "409",
            "422",
            "500",
        ):
            response_schema = operation["responses"][status_code]["content"][
                "application/json"
            ]["schema"]
            assert response_schema == {"$ref": "#/components/schemas/ErrorResponse"}
    assert "503" not in live["responses"]
    assert "503" in ready["responses"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_auth_openapi_declares_secret_input_and_cookie_transport() -> None:
    schema = TestClient(create_app(settings=make_test_settings())).get(
        "/openapi.json"
    ).json()
    login = schema["paths"]["/api/v1/auth/login"]["post"]
    current = schema["paths"]["/api/v1/auth/session"]["get"]
    logout = schema["paths"]["/api/v1/auth/logout"]["post"]
    login_request = schema["components"]["schemas"]["LoginRequest"]

    assert login["operationId"] == "auth_login"
    assert logout["operationId"] == "auth_logout"
    assert current["operationId"] == "auth_current_session"
    assert login["tags"] == ["auth"]
    assert logout["tags"] == ["auth"]
    assert current["tags"] == ["auth"]
    assert "security" not in login
    assert logout["security"] == [{"SessionCookie": []}]
    assert current["security"] == [{"SessionCookie": []}]
    assert schema["components"]["securitySchemes"] == {
        "SessionCookie": {
            "type": "apiKey",
            "in": "cookie",
            "name": "company_system_session",
        }
    }
    assert login_request["properties"]["password"]["format"] == "password"
    assert login_request["properties"]["password"]["writeOnly"] is True
    assert set(login_request["required"]) == {
        "organization_id",
        "login_name",
        "password",
    }
    login_response = schema["components"]["schemas"]["LoginResponse"]
    assert set(login_response["required"]) == {
        "capabilities",
        "expires_at",
        "user",
        "organization",
    }
    assert "session_token" not in login_response["properties"]
    assert "token_type" not in login_response["properties"]
    csrf_parameter = next(
        parameter
        for parameter in logout["parameters"]
        if parameter["name"] == "X-CSRF-Token"
    )
    assert csrf_parameter["in"] == "header"
    assert csrf_parameter["required"] is False
    assert logout["responses"]["204"] == {"description": "Successful Response"}
    current_response = schema["components"]["schemas"]["CurrentSessionResponse"]
    assert set(current_response["required"]) == {
        "capabilities",
        "expires_at",
        "user",
        "organization",
    }


def test_development_swagger_ui_remains_available() -> None:
    client = TestClient(create_app(settings=make_test_settings()))

    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_production_disables_swagger_and_openapi_routes() -> None:
    production_settings = AppSettings.model_validate(
        valid_settings_values(
            APP_ENV="production",
            DATABASE_URL=(
                "postgresql+psycopg://company_system_prod:production-only"
                "@database.internal/company_system_prod"
            ),
        )
    )
    client = TestClient(create_app(settings=production_settings))

    docs_response = client.get("/docs")
    openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 404
    assert openapi_response.status_code == 404
    assert docs_response.json()["error"]["code"] == "NOT_FOUND"
    assert openapi_response.json()["error"]["code"] == "NOT_FOUND"
