"""Track login session replacement without storing raw credentials.

Revision ID: 0025_session_replacement
Revises: 0024_document_exports
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_session_replacement"
down_revision: str | Sequence[str] | None = "0024_document_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow append-only security events to reference replaced sessions."""

    op.execute(
        """
        WITH ranked_sessions AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY organization_member_id
                       ORDER BY created_at DESC, id DESC
                   ) AS session_rank
            FROM sessions
            WHERE revoked_at IS NULL
        )
        UPDATE sessions
        SET revoked_at = GREATEST(
            sessions.created_at,
            LEAST(sessions.expires_at, CURRENT_TIMESTAMP)
        )
        FROM ranked_sessions
        WHERE sessions.id = ranked_sessions.id
          AND ranked_sessions.session_rank > 1
        """
    )
    op.create_index(
        "uq_sessions_one_unrevoked_per_membership",
        "sessions",
        ["organization_member_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.add_column(
        "login_security_events",
        sa.Column("session_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_login_security_events_session_id_sessions",
        "login_security_events",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_login_security_events_session_id",
        "login_security_events",
        ["session_id"],
    )
    op.drop_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        "event_type IN ('login_failed', 'login_rate_limited', 'login_succeeded', "
        "'session_replaced')",
    )


def downgrade() -> None:
    """Restore the pre-replacement login event contract."""

    op.execute(
        "ALTER TABLE login_security_events "
        "DISABLE TRIGGER trg_login_security_events_prevent_mutation"
    )
    op.execute(
        "UPDATE login_security_events SET event_type = 'login_succeeded' "
        "WHERE event_type = 'session_replaced'"
    )
    op.execute(
        "ALTER TABLE login_security_events "
        "ENABLE TRIGGER trg_login_security_events_prevent_mutation"
    )
    op.drop_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_login_security_events_type_allowed",
        "login_security_events",
        "event_type IN ('login_failed', 'login_rate_limited', 'login_succeeded')",
    )
    op.drop_index(
        "ix_login_security_events_session_id",
        table_name="login_security_events",
    )
    op.drop_constraint(
        "fk_login_security_events_session_id_sessions",
        "login_security_events",
        type_="foreignkey",
    )
    op.drop_column("login_security_events", "session_id")
    op.drop_index(
        "uq_sessions_one_unrevoked_per_membership",
        table_name="sessions",
    )
