"""Create statements, receipts, and allocation ledgers.

Revision ID: 0022_billing
Revises: 0021_pricing
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_billing"
down_revision: str | Sequence[str] | None = "0021_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "statements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(32), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tax_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("tax_rate_percent", sa.Numeric(7, 4)),
        sa.Column("rounding_scope", sa.String(16)),
        sa.Column("rounding_decimal_places", sa.Integer()),
        sa.Column("subtotal_before_rounding", sa.Numeric(18, 4), nullable=False),
        sa.Column("rounding_adjustment", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("grand_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("issue_idempotency_key", sa.Uuid()),
        sa.Column("cancellation_idempotency_key", sa.Uuid()),
        sa.Column("legacy_document_number", sa.String(128)),
        sa.Column("document_snapshot", sa.JSON()),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft','issued','partially_paid','paid','cancelled')",
            name="ck_statements_status",
        ),
        sa.CheckConstraint("period_from <= period_to", name="ck_statements_period"),
        sa.CheckConstraint("version > 0", name="ck_statements_version"),
        sa.CheckConstraint(
            "subtotal_before_rounding >= 0 AND subtotal >= 0 AND tax_amount >= 0 AND grand_total >= 0",
            name="ck_statements_amounts",
        ),
        sa.CheckConstraint(
            "rounding_scope IS NULL OR rounding_scope IN ('per_line','grand_total')",
            name="ck_statements_rounding_scope",
        ),
        sa.CheckConstraint(
            "rounding_decimal_places IS NULL OR rounding_decimal_places BETWEEN 0 AND 4",
            name="ck_statements_rounding_places",
        ),
        sa.CheckConstraint(
            "(tax_enabled = false AND tax_rate_percent IS NULL AND rounding_scope IS NULL AND rounding_decimal_places IS NULL AND tax_amount = 0) OR (tax_enabled = true AND tax_rate_percent > 0 AND tax_rate_percent <= 100 AND rounding_scope IS NOT NULL AND rounding_decimal_places IS NOT NULL)",
            name="ck_statements_tax_policy",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_statements_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_statements_creator_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_statements_org_id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_statements_idempotency"),
    )
    op.create_index(
        "uq_statements_org_number",
        "statements",
        ["organization_id", "document_number"],
        unique=True,
    )
    op.create_index(
        "uq_statements_org_issue_key",
        "statements",
        ["organization_id", "issue_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("issue_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "uq_statements_org_cancel_key",
        "statements",
        ["organization_id", "cancellation_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("cancellation_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "ix_statements_org_date_status",
        "statements",
        ["organization_id", "statement_date", "status", "id"],
    )
    op.create_table(
        "statement_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("source_pricing_item_id", sa.Uuid(), nullable=False),
        sa.Column("source_pricing_document_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("plate_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("die_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("line_no > 0 AND amount >= 0", name="ck_statement_items_values"),
        sa.CheckConstraint("btrim(content) <> ''", name="ck_statement_items_content"),
        sa.ForeignKeyConstraint(
            ["organization_id", "statement_id"],
            ["statements.organization_id", "statements.id"],
            name="fk_statement_items_statement_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_pricing_item_id"],
            ["pricing_items.organization_id", "pricing_items.id"],
            name="fk_statement_items_pricing_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_pricing_document_id"],
            ["pricing_documents.organization_id", "pricing_documents.id"],
            name="fk_statement_items_pricing_document_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_statement_items_org_id"),
        sa.UniqueConstraint(
            "organization_id", "statement_id", "line_no", name="uq_statement_items_line"
        ),
    )
    op.create_index(
        "uq_statement_items_active_source",
        "statement_items",
        ["organization_id", "source_pricing_item_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(32), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("payment_method", sa.String(64), nullable=False),
        sa.Column("reference_number", sa.String(128)),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(16), server_default="confirmed", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("reversal_idempotency_key", sa.Uuid()),
        sa.Column("legacy_document_number", sa.String(128)),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True)),
        sa.Column("reversal_reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('confirmed','reversed')", name="ck_receipts_status"),
        sa.CheckConstraint("amount > 0", name="ck_receipts_amount"),
        sa.CheckConstraint("btrim(payment_method) <> ''", name="ck_receipts_method"),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_receipts_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_receipts_creator_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_receipts_org_id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_receipts_idempotency"),
    )
    op.create_index(
        "uq_receipts_org_number", "receipts", ["organization_id", "document_number"], unique=True
    )
    op.create_index(
        "uq_receipts_org_reverse_key",
        "receipts",
        ["organization_id", "reversal_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("reversal_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "ix_receipts_org_date_status",
        "receipts",
        ["organization_id", "receipt_date", "status", "id"],
    )
    op.create_table(
        "receipt_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_receipt_allocations_amount"),
        sa.ForeignKeyConstraint(
            ["organization_id", "receipt_id"],
            ["receipts.organization_id", "receipts.id"],
            name="fk_receipt_allocations_receipt_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "statement_id"],
            ["statements.organization_id", "statements.id"],
            name="fk_receipt_allocations_statement_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "receipt_id", "statement_id", name="uq_receipt_allocations_pair"
        ),
    )
    op.create_index(
        "ix_receipt_allocations_statement_active",
        "receipt_allocations",
        ["organization_id", "statement_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_table("receipt_allocations")
    op.drop_table("receipts")
    op.drop_table("statement_items")
    op.drop_table("statements")
