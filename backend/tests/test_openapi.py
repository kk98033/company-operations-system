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
    assert ready["responses"]["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }

    for operation in (live, ready):
        for status_code in (
            "400",
            "401",
            "403",
            "404",
            "405",
            "409",
            "429",
            "422",
            "500",
        ):
            response_schema = operation["responses"][status_code]["content"]["application/json"][
                "schema"
            ]
            assert response_schema == {"$ref": "#/components/schemas/ErrorResponse"}
    assert "503" not in live["responses"]
    assert "503" in ready["responses"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]


def test_auth_openapi_declares_secret_input_and_cookie_transport() -> None:
    schema = TestClient(create_app(settings=make_test_settings())).get("/openapi.json").json()
    login = schema["paths"]["/api/v1/auth/login"]["post"]
    current = schema["paths"]["/api/v1/auth/session"]["get"]
    logout = schema["paths"]["/api/v1/auth/logout"]["post"]
    personal_sessions = schema["paths"]["/api/v1/auth/sessions"]["get"]
    company_sessions = schema["paths"]["/api/v1/auth/company-sessions"]["get"]
    revoke_session = schema["paths"][
        "/api/v1/auth/company-sessions/{session_id}/revoke"
    ]["post"]
    login_request = schema["components"]["schemas"]["LoginRequest"]

    assert login["operationId"] == "auth_login"
    assert logout["operationId"] == "auth_logout"
    assert current["operationId"] == "auth_current_session"
    assert personal_sessions["operationId"] == "auth_list_personal_sessions"
    assert company_sessions["operationId"] == "auth_list_company_sessions"
    assert revoke_session["operationId"] == "auth_revoke_company_session"
    assert login["tags"] == ["auth"]
    assert logout["tags"] == ["auth"]
    assert current["tags"] == ["auth"]
    assert "security" not in login
    assert logout["security"] == [{"SessionCookie": []}]
    assert current["security"] == [{"SessionCookie": []}]
    assert personal_sessions["security"] == [{"SessionCookie": []}]
    assert company_sessions["security"] == [{"SessionCookie": []}]
    assert revoke_session["security"] == [{"SessionCookie": []}]
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
    managed_session = schema["components"]["schemas"]["ManagedSessionResponse"]
    assert "token_digest" not in managed_session["properties"]
    assert "token" not in managed_session["properties"]
    assert login["responses"]["429"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    csrf_parameter = next(
        parameter for parameter in logout["parameters"] if parameter["name"] == "X-CSRF-Token"
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


def test_audit_openapi_is_read_only_bounded_and_cookie_protected() -> None:
    schema = TestClient(create_app(settings=make_test_settings())).get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/audit-logs"]["get"]
    parameters = {item["name"]: item for item in operation["parameters"]}

    assert operation["operationId"] == "audit_list"
    assert operation["tags"] == ["audit"]
    assert operation["security"] == [{"SessionCookie": []}]
    assert parameters["page_size"]["schema"]["maximum"] == 100
    assert parameters["request_id"]["in"] == "query"
    assert "post" not in schema["paths"]["/api/v1/audit-logs"]


def test_organization_profile_openapi_is_scoped_and_csrf_protected() -> None:
    schema = TestClient(create_app(settings=make_test_settings())).get("/openapi.json").json()
    path = schema["paths"]["/api/v1/organizations/current/profile"]

    assert path["get"]["operationId"] == "organization_profile_get"
    assert path["put"]["operationId"] == "organization_profile_update"
    assert path["get"]["security"] == [{"SessionCookie": []}]
    assert path["put"]["security"] == [{"SessionCookie": []}]
    update = schema["components"]["schemas"]["OrganizationProfileUpdate"]
    assert "organization_id" not in update["properties"]
    assert "logo" not in update["properties"]
    assert "expected_updated_at" in update["required"]


def test_organization_settings_openapi_keeps_fixed_policies_read_only() -> None:
    schema = TestClient(create_app(settings=make_test_settings())).get("/openapi.json").json()
    path = schema["paths"]["/api/v1/organizations/current/settings"]

    assert path["get"]["operationId"] == "organization_settings_get"
    assert path["put"]["operationId"] == "organization_settings_update"
    assert path["get"]["security"] == [{"SessionCookie": []}]
    assert path["put"]["security"] == [{"SessionCookie": []}]
    update = schema["components"]["schemas"]["OrganizationSettingsUpdate"]
    assert "document_numbering" not in update["properties"]
    assert "printing" not in update["properties"]
    assert "organization_id" not in update["properties"]
    assert "expected_updated_at" in update["required"]
    response = schema["components"]["schemas"]["OrganizationSettingsResponse"]
    assert "document_numbering" in response["required"]
    assert "printing" in response["required"]


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
