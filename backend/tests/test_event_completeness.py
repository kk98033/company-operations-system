"""Fail closed when an API mutation or sensitive read lacks declared evidence."""

from app.core.event_completeness import (
    MUTATION_EVENT_COVERAGE,
    SENSITIVE_READ_EVENT_COVERAGE,
)
from app.main import create_app
from tests.database_factory import make_database_resources
from tests.settings_factory import make_test_settings

_MUTATING_METHODS = {"post", "put", "patch", "delete"}


def _operations() -> dict[str, str]:
    schema = create_app(
        settings=make_test_settings(),
        database_resources=make_database_resources(),
        readiness_checks=[],
    ).openapi()
    return {
        operation["operationId"]: method
        for path in schema["paths"].values()
        for method, operation in path.items()
        if method in {"get", *_MUTATING_METHODS}
    }


def test_every_mutating_operation_has_declared_event_evidence() -> None:
    operations = _operations()
    mutations = {
        operation_id
        for operation_id, method in operations.items()
        if method in _MUTATING_METHODS
    }

    assert set(MUTATION_EVENT_COVERAGE) == mutations


def test_sensitive_read_matrix_references_real_get_operations() -> None:
    operations = _operations()

    assert set(SENSITIVE_READ_EVENT_COVERAGE) <= set(operations)
    assert all(
        operations[operation_id] == "get"
        for operation_id in SENSITIVE_READ_EVENT_COVERAGE
    )
    assert all(entry.event for entry in SENSITIVE_READ_EVENT_COVERAGE.values())
