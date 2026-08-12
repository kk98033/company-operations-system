"""Create login throttle state and append-only security events.

Revision ID: 0007_login_security
Revises: 0006_audit_foundation
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_login_security"
down_revision: str | Sequence[str] | None = "0006_audit_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create privacy-preserving login security storage."""

    op.create_table(
        "login_throttle_states",
        sa.Column("credential_fingerprint", sa.String(64), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "credential_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_login_throttle_states_fingerprint_format",
        ),
        sa.CheckConstraint(
            "failure_count >= 1",
            name="ck_login_throttle_states_failure_count_positive",
        ),
        sa.CheckConstraint(
            "last_failed_at >= window_started_at",
            name="ck_login_throttle_states_failure_time_order",
        ),
        sa.CheckConstraint(
            "blocked_until IS NULL OR blocked_until > last_failed_at",
            name="ck_login_throttle_states_blocked_after_failure",
        ),
        sa.PrimaryKeyConstraint("credential_fingerprint"),
    )
    op.create_table(
        "login_security_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("credential_fingerprint", sa.String(64), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=True),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('login_failed', 'login_rate_limited', 'login_succeeded')",
            name="ck_login_security_events_type_allowed",
        ),
        sa.CheckConstraint(
            "credential_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_login_security_events_fingerprint_format",
        ),
        sa.CheckConstraint(
            "failure_count IS NULL OR failure_count >= 0",
            name="ck_login_security_events_failure_count_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_login_security_events_fingerprint_created_at",
        "login_security_events",
        ["credential_fingerprint", "created_at"],
    )
    op.create_index(
        "ix_login_security_events_request_id",
        "login_security_events",
        ["request_id"],
    )
    op.create_index(
        "ix_login_security_events_created_at",
        "login_security_events",
        ["created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_login_security_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'login_security_events are append-only'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_login_security_events_prevent_mutation
        BEFORE UPDATE OR DELETE ON login_security_events
        FOR EACH ROW EXECUTE FUNCTION prevent_login_security_event_mutation()
        """
    )


def downgrade() -> None:
    """Remove login security storage while preserving Phase 1 foundations."""

    op.drop_table("login_security_events")
    op.execute("DROP FUNCTION prevent_login_security_event_mutation()")
    op.drop_table("login_throttle_states")
