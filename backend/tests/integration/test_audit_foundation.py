"""PostgreSQL acceptance tests for immutable transactional audit events."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.modules.audit import record_user_audit_event
from app.modules.audit.models import AuditLog
from app.modules.audit.sanitizer import REDACTED
from app.modules.authorization.models import Role
from app.modules.organizations.scope import OrganizationScope
from tests.integration.identity_test_support import seed_identity

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _scope_and_role(engine: Engine) -> tuple[OrganizationScope, UUID]:
    organization_id, user_id, membership_id, _ = seed_identity(engine)
    role_id = uuid4()
    role = Role(
        id=role_id,
        organization_id=organization_id,
        code="operator",
        name="Synthetic Operator",
    )
    with OrmSession(engine) as session, session.begin():
        session.add(role)
    return OrganizationScope(organization_id, membership_id, user_id), role_id


def test_business_change_and_sanitized_audit_commit_together(
    identity_engine: Engine,
) -> None:
    scope, role_id = _scope_and_role(identity_engine)
    request_id = uuid4()
    with OrmSession(identity_engine) as session, session.begin():
        session.execute(update(Role).where(Role.id == role_id).values(name="Updated Operator"))
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="role.update",
            entity_type="role",
            entity_id=role_id,
            reason="Synthetic acceptance",
            before={"name": "Synthetic Operator", "password": "canary"},
            after={"name": "Updated Operator"},
        )

    with OrmSession(identity_engine) as session:
        event = session.scalar(select(AuditLog).where(AuditLog.request_id == request_id))
        assert session.get(Role, role_id).name == "Updated Operator"
        assert event.before_data["password"] == REDACTED
        assert event.after_data == {"name": "Updated Operator"}
        assert event.actor_user_id == scope.actor_user_id


def test_business_change_and_audit_both_rollback_on_failure(
    identity_engine: Engine,
) -> None:
    scope, role_id = _scope_and_role(identity_engine)
    request_id = uuid4()

    with pytest.raises(RuntimeError, match="rollback"):
        with OrmSession(identity_engine) as session, session.begin():
            session.execute(update(Role).where(Role.id == role_id).values(name="Must Roll Back"))
            record_user_audit_event(
                session,
                scope=scope,
                request_id=request_id,
                action="role.update",
                entity_type="role",
                entity_id=role_id,
            )
            raise RuntimeError("rollback")

    with OrmSession(identity_engine) as session:
        assert session.get(Role, role_id).name == "Synthetic Operator"
        assert session.scalar(select(AuditLog).where(AuditLog.request_id == request_id)) is None


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_database_trigger_rejects_audit_mutation(
    identity_engine: Engine,
    operation: str,
) -> None:
    scope, role_id = _scope_and_role(identity_engine)
    with OrmSession(identity_engine) as session, session.begin():
        event = record_user_audit_event(
            session,
            scope=scope,
            request_id=uuid4(),
            action="role.update",
            entity_type="role",
            entity_id=role_id,
        )
        session.flush()
        event_id = event.id

    with OrmSession(identity_engine) as session:
        with pytest.raises(DBAPIError):
            with session.begin():
                if operation == "update":
                    session.execute(
                        update(AuditLog).where(AuditLog.id == event_id).values(reason="tampered")
                    )
                else:
                    session.delete(session.get(AuditLog, event_id))


def test_actor_membership_cannot_cross_organization(
    identity_engine: Engine,
) -> None:
    scope_a, role_a_id = _scope_and_role(identity_engine)
    scope_b, _ = _scope_and_role(identity_engine)
    forged_scope = OrganizationScope(
        organization_id=scope_a.organization_id,
        organization_member_id=scope_b.organization_member_id,
        actor_user_id=scope_b.actor_user_id,
    )

    with OrmSession(identity_engine) as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                record_user_audit_event(
                    session,
                    scope=forged_scope,
                    request_id=uuid4(),
                    action="role.update",
                    entity_type="role",
                    entity_id=role_a_id,
                )


def test_system_audit_event_requires_existing_organization(
    identity_engine: Engine,
) -> None:
    with OrmSession(identity_engine) as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(
                    AuditLog(
                        organization_id=uuid4(),
                        actor_kind="system",
                        action="import.complete",
                        entity_type="import_run",
                        event_status="success",
                        request_id=uuid4(),
                    )
                )
