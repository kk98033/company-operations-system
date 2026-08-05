import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.list_contract_app import register_list_contract_route
from tests.settings_factory import make_test_settings


def make_client() -> TestClient:
    app = create_app(settings=make_test_settings())
    register_list_contract_route(app)
    return TestClient(app)


def test_list_contract_returns_bounded_defaults_and_filter_summary() -> None:
    response = make_client().get("/_test/examples")

    assert response.status_code == 200
    assert response.json() == {
        "items": [{"id": 1, "name": "Example"}],
        "meta": {
            "pagination": {
                "page": 1,
                "page_size": 25,
                "total_items": 26,
                "total_pages": 2,
                "has_previous": False,
                "has_next": True,
            },
            "sort": {"field": "created_at", "direction": "desc"},
            "filters": {"keyword": None, "date_from": None, "date_to": None},
        },
    }


def test_list_contract_accepts_composed_query_primitives() -> None:
    response = make_client().get(
        "/_test/examples",
        params={
            "page": 2,
            "page_size": 20,
            "sort_by": "name",
            "sort_direction": "asc",
            "keyword": "  carton ",
            "date_from": "2026-08-01",
            "date_to": "2026-08-05",
        },
    )

    assert response.status_code == 200
    meta = response.json()["meta"]
    assert meta["pagination"]["page"] == 2
    assert meta["sort"] == {"field": "name", "direction": "asc"}
    assert meta["filters"] == {
        "keyword": "carton",
        "date_from": "2026-08-01",
        "date_to": "2026-08-05",
    }


def test_endpoint_sort_enum_rejects_arbitrary_field_without_echoing_input() -> None:
    malicious_field = "password_column_should_not_leak"
    response = make_client().get(
        "/_test/examples",
        params={"sort_by": malicious_field},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["loc"] == ["query", "sort_by"]
    assert malicious_field not in response.text


def test_inverted_date_range_uses_safe_error_envelope() -> None:
    response = make_client().get(
        "/_test/examples",
        params={"date_from": "2026-08-06", "date_to": "2026-08-05"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["loc"] == [
        "query",
        "date_to",
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"keyword": "x" * 101},
        {"sort_direction": "sideways"},
        {"date_from": "not-a-date"},
    ],
)
def test_list_contract_http_boundaries_use_error_envelope(
    params: dict[str, int | str],
) -> None:
    response = make_client().get("/_test/examples", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_contract_openapi_exposes_enum_and_shared_envelopes() -> None:
    schema = make_client().get("/openapi.json").json()
    operation = schema["paths"]["/_test/examples"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    sort_schema = parameters["sort_by"]["schema"]
    assert sort_schema["$ref"] == "#/components/schemas/ExampleSortField"
    assert schema["components"]["schemas"]["ExampleSortField"]["enum"] == [
        "created_at",
        "name",
    ]
    assert parameters["page_size"]["schema"]["maximum"] == 100
    assert operation["responses"]["422"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ErrorResponse"}
    assert operation["responses"]["500"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ErrorResponse"}
