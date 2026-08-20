"""Expand append-only login events into authenticated security evidence.

Revision ID: 0027_security_events
Revises: 0026_session_management
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_security_events"
down_revision: str | Sequence[str] | None = "0026_session_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LOGIN_TYPES = (
    "'login_failed', 'login_rate_limited', 'login_succeeded', 'session_replaced'"
)
_AUTHENTICATED_TYPES = (
    "'logout_succeeded', 'session_revoked', "
    "'membership_sessions_revoked', 'permission_denied'"
)


def upgrade() -> None:
    """Add actor, target, and capability context without storing credentials."""

    op.alter_column(
        "login_security_events",
        "credential_fingerprint",
        existing_type=sa.String(64),
        nullable=True,
    )
    op.add_column("login_security_events", sa.Column("organization_id", sa.Uuid()))
    op.add_column("login_security_events", sa.Column("actor_membership_id", sa.Uuid()))
    op.add_column("login_security_events", sa.Column("actor_user_id", sa.Uuid()))
    op.add_column("login_security_events", sa.Column("target_type", sa.String(64)))
    op.add_column("login_security_events", sa.Column("target_id", sa.Uuid()))
    op.add_column("login_security_events", sa.Column("capability", sa.String(128)))
    op.create_foreign_key(
        "fk_login_security_events_organization_id_organizations",
        "login_security_events",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_login_security_events_actor_organization_members",
        "login_security_events",
        "organization_members",
        ["organization_id", "actor_membership_id", "actor_user_id"],
        ["organization_id", "id", "user_id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_login_security_events_fingerprint_format",
        "login_security_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        f"event_type IN ({_LOGIN_TYPES}, {_AUTHENTICATED_TYPES})",
    )
    op.create_check_constraint(
        "ck_login_security_events_fingerprint_format",
        "login_security_events",
        "credential_fingerprint IS NULL OR "
        "credential_fingerprint ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_login_security_events_identity_consistent",
        "login_security_events",
        f"(event_type IN ({_LOGIN_TYPES}) AND credential_fingerprint IS NOT NULL) OR "
        f"(event_type IN ({_AUTHENTICATED_TYPES}) AND "
        "credential_fingerprint IS NULL AND organization_id IS NOT NULL AND "
        "actor_membership_id IS NOT NULL AND actor_user_id IS NOT NULL AND "
        "session_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_login_security_events_target_consistent",
        "login_security_events",
        "(target_type IS NULL AND target_id IS NULL) OR "
        "(target_type IS NOT NULL AND target_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_login_security_events_target_type_format",
        "login_security_events",
        "target_type IS NULL OR (target_type = lower(btrim(target_type)) AND "
        "target_type ~ '^[a-z][a-z0-9_]*$')",
    )
    op.create_check_constraint(
        "ck_login_security_events_capability_format",
        "login_security_events",
        "capability IS NULL OR (capability = lower(btrim(capability)) AND "
        "capability ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$')",
    )
    op.create_index(
        "ix_login_security_events_organization_id_created_at",
        "login_security_events",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_login_security_events_actor_membership_id_created_at",
        "login_security_events",
        ["actor_membership_id", "created_at"],
    )
    op.execute(
        "CREATE TRIGGER trg_login_security_events_prevent_truncate "
        "BEFORE TRUNCATE ON login_security_events FOR EACH STATEMENT "
        "EXECUTE FUNCTION prevent_login_security_event_mutation()"
    )
    op.execute(
        "CREATE TRIGGER trg_audit_logs_prevent_truncate "
        "BEFORE TRUNCATE ON audit_logs FOR EACH STATEMENT "
        "EXECUTE FUNCTION prevent_audit_log_mutation()"
    )


def downgrade() -> None:
    """Remove authenticated-only event rows and restore the login contract."""

    op.execute(
        "DROP TRIGGER IF EXISTS trg_audit_logs_prevent_truncate ON audit_logs"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_login_security_events_prevent_truncate "
        "ON login_security_events"
    )
    op.execute(
        "ALTER TABLE login_security_events "
        "DISABLE TRIGGER trg_login_security_events_prevent_mutation"
    )
    op.execute(
        f"DELETE FROM login_security_events WHERE event_type IN ({_AUTHENTICATED_TYPES})"
    )
    op.execute(
        "ALTER TABLE login_security_events "
        "ENABLE TRIGGER trg_login_security_events_prevent_mutation"
    )
    op.drop_index(
        "ix_login_security_events_actor_membership_id_created_at",
        table_name="login_security_events",
    )
    op.drop_index(
        "ix_login_security_events_organization_id_created_at",
        table_name="login_security_events",
    )
    op.drop_constraint(
        "ck_login_security_events_capability_format",
        "login_security_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_login_security_events_target_type_format",
        "login_security_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_login_security_events_target_consistent",
        "login_security_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_login_security_events_identity_consistent",
        "login_security_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_login_security_events_fingerprint_format",
        "login_security_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        f"event_type IN ({_LOGIN_TYPES})",
    )
    op.create_check_constraint(
        "ck_login_security_events_fingerprint_format",
        "login_security_events",
        "credential_fingerprint ~ '^[0-9a-f]{64}$'",
    )
    op.drop_constraint(
        "fk_login_security_events_actor_organization_members",
        "login_security_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_login_security_events_organization_id_organizations",
        "login_security_events",
        type_="foreignkey",
    )
    for column in (
        "capability",
        "target_id",
        "target_type",
        "actor_user_id",
        "actor_membership_id",
        "organization_id",
    ):
        op.drop_column("login_security_events", column)
    op.alter_column(
        "login_security_events",
        "credential_fingerprint",
        existing_type=sa.String(64),
        nullable=False,
    )
