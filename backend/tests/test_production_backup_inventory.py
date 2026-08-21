"""Machine-readable production backup inventory contract."""

import json
from pathlib import Path

INVENTORY_PATH = (
    Path(__file__).resolve().parents[2]
    / "infra"
    / "production"
    / "backup-inventory.json"
)


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def test_production_inventory_is_complete_and_contains_no_secret_values() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert inventory["schema_version"] == 1
    assert inventory["deployment_model"] == "one_release_isolated_per_company"
    assert inventory["recovery_targets"] == {
        "rpo_minutes": 15,
        "rto_hours": 4,
        "status": "target_pending_restore_drill",
    }
    assets = inventory["assets"]
    assert len(assets) == 5
    assert len({asset["id"] for asset in assets}) == len(assets)
    assert all(
        asset[required]
        for asset in assets
        for required in (
            "system_of_record",
            "contains",
            "backup",
            "retention",
            "recovery_dependency",
            "owner",
        )
    )
    forbidden_keys = {"value", "password", "token", "dsn", "secret_value"}
    assert forbidden_keys.isdisjoint(set(_walk_keys(inventory)))
