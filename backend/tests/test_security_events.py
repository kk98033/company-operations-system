"""Authenticated security-event contracts never contain browser credentials."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.modules.auth.services import (
    AuthenticatedSession,
    record_authenticated_security_event,
)


def _context() -> AuthenticatedSession:
    return AuthenticatedSession(
        expires_at=datetime.now(UTC) + timedelta(hours=8),
        organization_member_id=uuid4(),
        user_id=uuid4(),
        login_name="synthetic.operator",
        display_name="Synthetic Operator",
        organization_id=uuid4(),
        organization_name="Synthetic Organization",
        session_id=uuid4(),
    )


def test_authenticated_event_stages_only_internal_references() -> None:
    session = Mock()
    context = _context()
    request_id = uuid4()
    target_id = uuid4()

    event = record_authenticated_security_event(
        session,
        context=context,
        request_id=request_id,
        event_type="permission_denied",
        target_type="auth_session",
        target_id=target_id,
        capability="sessions.manage",
    )

    session.add.assert_called_once_with(event)
    session.commit.assert_not_called()
    assert event.organization_id == context.organization_id
    assert event.actor_membership_id == context.organization_member_id
    assert event.actor_user_id == context.user_id
    assert event.session_id == context.session_id
    assert event.credential_fingerprint is None
    assert event.target_id == target_id
    assert event.capability == "sessions.manage"
    assert "token" not in event.__dict__
    assert "password" not in event.__dict__


@pytest.mark.parametrize(
    ("target_type", "target_id", "capability"),
    [
        ("Invalid-Type", uuid4(), None),
        ("auth_session", None, None),
        (None, uuid4(), None),
        (None, None, "Sessions.Manage"),
    ],
)
def test_authenticated_event_rejects_unbounded_context(
    target_type: str | None,
    target_id: UUID | None,
    capability: str | None,
) -> None:
    with pytest.raises(ValueError):
        record_authenticated_security_event(
            Mock(),
            context=_context(),
            request_id=uuid4(),
            event_type="permission_denied",
            target_type=target_type,
            target_id=target_id,
            capability=capability,
        )
