"""Create company work orders and private attachments.

Revision ID: 0017_work_orders
Revises: 0016_production_cases
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_work_orders"
down_revision: str | Sequence[str] | None = "0016_production_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_quotation_items_organization_id_id",
        "quotation_items",
        ["organization_id", "id"],
    )
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(32), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_order_number", sa.String(100), nullable=True),
        sa.Column("organization_snapshot", sa.JSON(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("order_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("plate_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("die_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("papers", sa.JSON(), nullable=False),
        sa.Column("print_specification", sa.JSON(), nullable=False),
        sa.Column("processes", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("source_quotation_item_id", sa.Uuid(), nullable=True),
        sa.Column("source_work_order_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_document_number", sa.String(128), nullable=True),
        sa.Column("legacy_source_table", sa.String(64), nullable=True),
        sa.Column("legacy_source_key", sa.String(128), nullable=True),
        sa.Column("document_snapshot", sa.JSON(), nullable=True),
        sa.Column("print_metadata", sa.JSON(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'void')", name="ck_work_orders_status"
        ),
        sa.CheckConstraint(
            "btrim(document_number) <> '' AND btrim(product_name) <> ''",
            name="ck_work_orders_required_text",
        ),
        sa.CheckConstraint("order_quantity > 0", name="ck_work_orders_quantity_positive"),
        sa.CheckConstraint(
            "unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0",
            name="ck_work_orders_money_nonnegative",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND voided_at IS NULL AND void_reason IS NULL) OR (status = 'confirmed' AND confirmed_at IS NOT NULL AND voided_at IS NULL AND void_reason IS NULL) OR (status = 'void' AND voided_at IS NOT NULL AND btrim(void_reason) <> '')",
            name="ck_work_orders_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "case_id"],
            ["production_cases.organization_id", "production_cases.id"],
            name="fk_work_orders_case_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_work_orders_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_quotation_item_id"],
            ["quotation_items.organization_id", "quotation_items.id"],
            name="fk_work_orders_quote_item_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_work_orders_source_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_work_orders_org_id"),
    )
    op.create_index(
        "uq_work_orders_org_number",
        "work_orders",
        ["organization_id", "document_number"],
        unique=True,
    )
    op.create_index(
        "uq_work_orders_org_quote_item",
        "work_orders",
        ["organization_id", "source_quotation_item_id"],
        unique=True,
        postgresql_where=sa.text("source_quotation_item_id IS NOT NULL"),
    )
    op.create_index(
        "ix_work_orders_org_case", "work_orders", ["organization_id", "case_id", "document_number"]
    )
    op.create_index(
        "ix_work_orders_org_due_status",
        "work_orders",
        ["organization_id", "delivery_date", "status", "id"],
    )
    op.create_table(
        "work_order_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 5242880", name="ck_work_order_attachments_size"
        ),
        sa.CheckConstraint(
            "octet_length(content) = size_bytes", name="ck_work_order_attachments_content_size"
        ),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_work_order_attachments_sha256"),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_work_order_attachments_order_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_order_attachments_org_order",
        "work_order_attachments",
        ["organization_id", "work_order_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("work_order_attachments")
    op.drop_table("work_orders")
    op.drop_constraint(
        "uq_quotation_items_organization_id_id",
        "quotation_items",
        type_="unique",
    )
