"""PostgreSQL API acceptance for scoped, permission-guarded audit reads."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit import record_user_audit_event
from app.modules.audit.models import AuditLog
from app.modules.audit.sanitizer import REDACTED
from app.modules.authorization.models import (
    OrganizationMemberRole,
    Permission,
    Role,
    RolePermission,
)
from app.modules.organizations.scope import OrganizationScope
from tests.integration.auth_test_support import create_auth_identity, make_auth_client

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _grant_audit_read(
    engine: Engine,
    *,
    organization_id,
    membership_id,
) -> None:
    permission_id = uuid4()
    role_id = uuid4()
    with OrmSession(engine) as session, session.begin():
        session.add_all(
            [
                Permission(
                    id=permission_id,
                    code="audit.read",
                    name="Read synthetic audit history",
                ),
                Role(
                    id=role_id,
                    organization_id=organization_id,
                    code="auditor",
                    name="Synthetic Auditor",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                RolePermission(
                    role_id=role_id,
                    permission_id=permission_id,
                ),
                OrganizationMemberRole(
                    organization_id=organization_id,
                    organization_member_id=membership_id,
                    role_id=role_id,
                ),
            ]
        )


def _login(client, identity) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "organization_id": str(identity.organization_id),
            "login_name": identity.login_name,
            "password": identity.password.get_secret_value(),
        },
    )
    assert response.status_code == 200


def test_audit_api_is_permission_guarded_scoped_and_sanitized(
    identity_engine: Engine,
) -> None:
    identity_a = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-A-{uuid4()}"),
    )
    identity_b = create_auth_identity(
        identity_engine,
        password=SecretStr(f"Synthetic-B-{uuid4()}"),
    )
    _grant_audit_read(
        identity_engine,
        organization_id=identity_a.organization_id,
        membership_id=identity_a.membership_id,
    )
    request_a = uuid4()
    request_b = uuid4()
    with OrmSession(identity_engine) as session, session.begin():
        record_user_audit_event(
            session,
            scope=OrganizationScope(
                identity_a.organization_id,
                identity_a.membership_id,
                identity_a.user_id,
            ),
            request_id=request_a,
            action="role.update",
            entity_type="role",
            reason="Company A only",
            before={"password": "must-never-leak", "name": "Before"},
            after={"name": "After"},
        )
        record_user_audit_event(
            session,
            scope=OrganizationScope(
                identity_b.organization_id,
                identity_b.membership_id,
                identity_b.user_id,
            ),
            request_id=request_b,
            action="role.update",
            entity_type="role",
            reason="Company B hidden",
        )

    client_a = make_auth_client(identity_engine)
    _login(client_a, identity_a)
    response = client_a.get("/api/v1/audit-logs")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["pagination"]["total_items"] == 1
    assert body["items"][0]["request_id"] == str(request_a)
    assert body["items"][0]["before_data"]["password"] == REDACTED
    assert "must-never-leak" not in response.text
    assert "Company B hidden" not in response.text

    client_b = make_auth_client(identity_engine)
    _login(client_b, identity_b)
    denied = client_b.get("/api/v1/audit-logs")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PERMISSION_DENIED"
    with OrmSession(identity_engine) as session:
        read_event = session.scalar(
            select(AuditLog).where(
                AuditLog.organization_id == identity_a.organization_id,
                AuditLog.action == "audit.read",
            )
        )
    assert read_event is not None
    assert read_event.after_data == {"result_count": 1, "total_items": 1}
    assert str(read_event.request_id) == response.headers["x-request-id"]
