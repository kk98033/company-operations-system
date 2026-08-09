"""Create append-only audit log foundation.

Revision ID: 0006_audit_foundation
Revises: 0005_authorization_foundation
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_audit_foundation"
down_revision: str | Sequence[str] | None = "0005_authorization_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create immutable audit storage without business-domain tables."""

    op.create_unique_constraint(
        "uq_organization_members_organization_id_id_user_id",
        "organization_members",
        ["organization_id", "id", "user_id"],
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_kind", sa.String(16), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("document_number", sa.String(128), nullable=True),
        sa.Column(
            "event_status",
            sa.String(16),
            server_default="success",
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action = lower(btrim(action)) AND "
            "action ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_audit_logs_action_format",
        ),
        sa.CheckConstraint(
            "entity_type = lower(btrim(entity_type)) AND "
            "entity_type ~ '^[a-z][a-z0-9_]*$'",
            name="ck_audit_logs_entity_type_format",
        ),
        sa.CheckConstraint(
            "event_status IN ('success', 'failure')",
            name="ck_audit_logs_event_status_allowed",
        ),
        sa.CheckConstraint(
            "actor_kind IN ('user', 'system')",
            name="ck_audit_logs_actor_kind_allowed",
        ),
        sa.CheckConstraint(
            "(actor_kind = 'user' AND actor_membership_id IS NOT NULL "
            "AND actor_user_id IS NOT NULL) OR "
            "(actor_kind = 'system' AND actor_membership_id IS NULL "
            "AND actor_user_id IS NULL)",
            name="ck_audit_logs_actor_identity_consistent",
        ),
        sa.CheckConstraint(
            "reason IS NULL OR btrim(reason) <> ''",
            name="ck_audit_logs_reason_nonblank",
        ),
        sa.CheckConstraint(
            "document_number IS NULL OR btrim(document_number) <> ''",
            name="ck_audit_logs_document_number_nonblank",
        ),
        sa.CheckConstraint(
            "before_data IS NULL OR jsonb_typeof(before_data) = 'object'",
            name="ck_audit_logs_before_data_object",
        ),
        sa.CheckConstraint(
            "after_data IS NULL OR jsonb_typeof(after_data) = 'object'",
            name="ck_audit_logs_after_data_object",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_audit_logs_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_audit_logs_actor_organization_members",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_organization_id_created_at",
        "audit_logs",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_organization_id_entity_type_entity_id",
        "audit_logs",
        ["organization_id", "entity_type", "entity_id"],
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.execute(
        """
        CREATE FUNCTION prevent_audit_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs are append-only' USING ERRCODE = '55000';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_logs_prevent_mutation
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation()
        """
    )


def downgrade() -> None:
    """Remove audit storage while preserving identity and authorization."""

    op.drop_table("audit_logs")
    op.execute("DROP FUNCTION prevent_audit_log_mutation()")
    op.drop_constraint(
        "uq_organization_members_organization_id_id_user_id",
        "organization_members",
        type_="unique",
    )
