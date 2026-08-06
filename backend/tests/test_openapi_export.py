import json
import re

from scripts.export_openapi import serialize_openapi


def test_openapi_export_is_deterministic_and_has_unique_operation_ids() -> None:
    first_export = serialize_openapi()
    second_export = serialize_openapi()

    assert first_export == second_export
    assert first_export.endswith("\n")

    schema = json.loads(first_export)
    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method in {"delete", "get", "patch", "post", "put"}
    ]

    assert operation_ids
    assert len(operation_ids) == len(set(operation_ids))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", value) for value in operation_ids)
