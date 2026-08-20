"""PostgreSQL acceptance for scoped Session listing and remote revocation."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit.models import AuditLog
from app.modules.auth.models import LoginSecurityEvent, Session
from tests.integration.auth_test_support import (
    create_auth_identity,
    create_auth_member,
    make_auth_client,
)
from tests.integration.work_order_test_support import grant

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _login(client, identity, *, user_agent: str = "Synthetic Browser") -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={"User-Agent": user_agent},
        json={
            "organization_id": str(identity.organization_id),
            "login_name": identity.login_name,
            "password": identity.password.get_secret_value(),
        },
    )
    assert response.status_code == 200, response.text


def _csrf(client) -> str:
    value = client.cookies.get("company_system_csrf")
    assert value is not None
    return value


def test_personal_history_is_scoped_and_contains_only_safe_client_summary(
    identity_engine: Engine,
) -> None:
    identity = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-{uuid4()}"),
    )
    other = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-OTHER-{uuid4()}"),
    )
    client = make_auth_client(identity_engine)
    raw_agent = "Mozilla/5.0 (Windows NT 10.0) Chrome/140.0.0.0 SecretMarker"
    _login(client, identity, user_agent=raw_agent)
    _login(client, identity, user_agent=raw_agent)
    _login(make_auth_client(identity_engine), other)

    response = client.get("/api/v1/auth/sessions")

    assert response.status_code == 200
    body = response.json()
    assert body["total_items"] == 2
    assert sum(item["is_current"] for item in body["items"]) == 1
    assert {item["status"] for item in body["items"]} == {"active", "revoked"}
    assert {item["client_summary"] for item in body["items"]} == {"Chrome／Windows"}
    assert str(other.user_id) not in response.text
    assert raw_agent not in response.text
    with OrmSession(identity_engine) as session:
        summaries = session.scalars(
            select(Session.client_summary).where(
                Session.organization_member_id == identity.membership_id
            )
        ).all()
    assert summaries == ["Chrome／Windows", "Chrome／Windows"]


def test_company_manager_can_revoke_one_session_with_scoped_audit(
    identity_engine: Engine,
) -> None:
    manager = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-MANAGER-{uuid4()}"),
    )
    target = create_auth_member(
        identity_engine,
        organization_id=manager.organization_id,
        password=SecretStr(f"Synthetic-TARGET-{uuid4()}"),
    )
    outsider = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-OUTSIDE-{uuid4()}"),
    )
    grant(identity_engine, manager, "sessions.manage")
    manager_client = make_auth_client(identity_engine)
    target_client = make_auth_client(identity_engine)
    outsider_client = make_auth_client(identity_engine)
    _login(manager_client, manager)
    _login(target_client, target)
    _login(outsider_client, outsider)

    listed = manager_client.get("/api/v1/auth/company-sessions")
    assert listed.status_code == 200
    assert {item["user"]["id"] for item in listed.json()["items"]} == {
        str(manager.user_id),
        str(target.user_id),
    }
    target_row = next(
        item for item in listed.json()["items"] if item["user"]["id"] == str(target.user_id)
    )
    revoked = manager_client.post(
        f"/api/v1/auth/company-sessions/{target_row['id']}/revoke",
        json={"reason": "員工要求登出遺失裝置"},
        headers={"X-CSRF-Token": _csrf(manager_client)},
    )

    assert revoked.status_code == 204
    assert target_client.get("/api/v1/auth/session").status_code == 401
    assert manager_client.get("/api/v1/auth/session").status_code == 200
    assert outsider_client.get("/api/v1/auth/session").status_code == 200
    with OrmSession(identity_engine) as session:
        event = session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == manager.organization_id,
                AuditLog.action == "session.revoke",
            )
        )
        security_event = session.scalar(
            select(LoginSecurityEvent).where(
                LoginSecurityEvent.event_type == "session_revoked"
            )
        )
    assert event is not None
    assert event.entity_id == UUID(target_row["id"])
    assert event.reason == "員工要求登出遺失裝置"
    assert security_event is not None
    assert security_event.session_id is not None
    assert security_event.target_type == "auth_session"
    assert security_event.target_id == UUID(target_row["id"])


def test_permission_cross_company_and_revoke_all_boundaries(identity_engine: Engine) -> None:
    manager = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-MANAGER-{uuid4()}"),
    )
    target = create_auth_member(
        identity_engine,
        organization_id=manager.organization_id,
        password=SecretStr(f"Synthetic-TARGET-{uuid4()}"),
    )
    outsider = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-OUTSIDE-{uuid4()}"),
    )
    grant(identity_engine, manager, "sessions.manage")
    manager_client = make_auth_client(identity_engine)
    target_client = make_auth_client(identity_engine)
    outsider_client = make_auth_client(identity_engine)
    _login(manager_client, manager)
    _login(target_client, target)
    _login(outsider_client, outsider)

    denied = target_client.get("/api/v1/auth/company-sessions")
    assert denied.status_code == 403
    cross_company = manager_client.post(
        f"/api/v1/auth/company-sessions/{outsider_client.get('/api/v1/auth/sessions').json()['items'][0]['id']}/revoke",
        json={"reason": "不可跨公司撤銷"},
        headers={"X-CSRF-Token": _csrf(manager_client)},
    )
    assert cross_company.status_code == 404
    assert outsider_client.get("/api/v1/auth/session").status_code == 200

    revoked_all = manager_client.post(
        "/api/v1/auth/company-sessions/revoke-membership",
        json={
            "organization_member_id": str(target.membership_id),
            "reason": "人員離職撤銷全部登入",
        },
        headers={"X-CSRF-Token": _csrf(manager_client)},
    )
    assert revoked_all.status_code == 204
    assert target_client.get("/api/v1/auth/session").status_code == 401
    with OrmSession(identity_engine) as session:
        denied_event = session.scalar(
            select(LoginSecurityEvent).where(
                LoginSecurityEvent.event_type == "permission_denied",
                LoginSecurityEvent.actor_user_id == target.user_id,
            )
        )
        revoked_all_event = session.scalar(
            select(LoginSecurityEvent).where(
                LoginSecurityEvent.event_type == "membership_sessions_revoked",
                LoginSecurityEvent.target_id == target.membership_id,
            )
        )
    assert denied_event is not None
    assert denied_event.capability == "sessions.manage"
    assert denied_event.request_id == UUID(denied.headers["x-request-id"])
    assert revoked_all_event is not None
