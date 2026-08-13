"""Persist immutable generated PDF exports.

Revision ID: 0024_document_exports
Revises: 0023_billing_invariants
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_document_exports"
down_revision: str | Sequence[str] | None = "0023_billing_invariants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(20), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(128), nullable=False),
        sa.Column("document_version", sa.String(64), nullable=False),
        sa.Column("template_version", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('quotation','work_order','shipment','statement')",
            name="ck_document_exports_type",
        ),
        sa.CheckConstraint("content_type = 'application/pdf'", name="ck_document_exports_pdf"),
        sa.CheckConstraint(
            "byte_size > 0 AND octet_length(content) = byte_size", name="ck_document_exports_size"
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_document_exports_sha256"),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_document_exports_creator_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "document_type",
            "document_id",
            "document_version",
            "template_version",
            name="uq_document_exports_version",
        ),
    )
    op.create_index(
        "ix_document_exports_org_document",
        "document_exports",
        ["organization_id", "document_type", "document_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION prevent_document_export_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'document exports are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_exports_immutable
        BEFORE UPDATE OR DELETE ON document_exports
        FOR EACH ROW EXECUTE FUNCTION prevent_document_export_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_document_exports_immutable ON document_exports")
    op.execute("DROP FUNCTION prevent_document_export_mutation()")
    op.drop_index("ix_document_exports_org_document", table_name="document_exports")
    op.drop_table("document_exports")
