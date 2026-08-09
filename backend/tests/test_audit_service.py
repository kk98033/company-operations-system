"""Audit sanitization and transaction-ownership unit contracts."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.modules.audit.sanitizer import REDACTED, TRUNCATED, sanitize_audit_payload
from app.modules.audit.services import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope


def _scope() -> OrganizationScope:
    return OrganizationScope(uuid4(), uuid4(), uuid4())


def test_sanitizer_redacts_nested_secrets_bytes_and_bounds_large_values() -> None:
    payload = {
        "status": "confirmed",
        "password": "plain-canary",
        "password_hash": "hash-canary",
        "nested": {
            "csrf-token": "csrf-canary",
            "safe_secretary_note": "conservative-redaction",
            "raw_file": b"file-canary",
        },
        "secret_object": SecretStr("secret-canary"),
        "amount": Decimal("12.50"),
        "occurred_at": datetime(2026, 8, 9, tzinfo=UTC),
        "long_note": "x" * 2_100,
    }

    sanitized = sanitize_audit_payload(payload)

    assert sanitized["status"] == "confirmed"
    assert sanitized["password"] == REDACTED
    assert sanitized["password_hash"] == REDACTED
    assert sanitized["nested"]["csrf-token"] == REDACTED
    assert sanitized["nested"]["safe_secretary_note"] == REDACTED
    assert sanitized["nested"]["raw_file"] == REDACTED
    assert sanitized["secret_object"] == REDACTED
    assert sanitized["amount"] == "12.50"
    assert sanitized["long_note"].endswith(TRUNCATED)
    assert "plain-canary" not in str(sanitized)
    assert "hash-canary" not in str(sanitized)
    assert "secret-canary" not in str(sanitized)
    assert "file-canary" not in str(sanitized)


def test_record_event_stages_sanitized_row_without_committing() -> None:
    session = Mock()
    scope = _scope()
    request_id = uuid4()

    event = record_user_audit_event(
        session,
        scope=scope,
        request_id=request_id,
        action="work_order.confirm",
        entity_type="work_order",
        entity_id=uuid4(),
        reason="  公司確認  ",
        before={"status": "draft", "session_token": "raw-canary"},
        after={"status": "confirmed"},
    )

    session.add.assert_called_once_with(event)
    session.commit.assert_not_called()
    session.flush.assert_not_called()
    assert event.organization_id == scope.organization_id
    assert event.actor_membership_id == scope.organization_member_id
    assert event.actor_user_id == scope.actor_user_id
    assert event.request_id == request_id
    assert event.reason == "公司確認"
    assert event.before_data["session_token"] == REDACTED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("action", "Admin"),
        ("entity_type", "work-order"),
        ("event_status", "unknown"),
        ("reason", "   "),
    ],
)
def test_record_event_rejects_invalid_contract(field: str, value: str) -> None:
    arguments = {
        "action": "work_order.confirm",
        "entity_type": "work_order",
        "event_status": "success",
        "reason": None,
    }
    arguments[field] = value

    with pytest.raises(ValueError):
        record_user_audit_event(
            Mock(),
            scope=_scope(),
            request_id=uuid4(),
            **arguments,
        )
