"""Create quotation headers and details."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_quotations"
down_revision: str | Sequence[str] | None = "0014_document_sequences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(32), nullable=False),
        sa.Column("quotation_date", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("organization_snapshot", sa.JSON(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("source_quotation_id", sa.Uuid(), nullable=True),
        sa.Column("legacy_document_number", sa.String(128), nullable=True),
        sa.Column("legacy_tax_included_raw", sa.String(16), nullable=True),
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
            "status IN ('draft', 'confirmed', 'void')", name="ck_quotations_status_allowed"
        ),
        sa.CheckConstraint(
            "btrim(document_number) <> ''", name="ck_quotations_document_number_nonblank"
        ),
        sa.CheckConstraint(
            "(legacy_source_table IS NULL) = (legacy_source_key IS NULL)",
            name="ck_quotations_legacy_source_pair",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND voided_at IS NULL AND void_reason IS NULL) "
            "OR (status = 'confirmed' AND confirmed_at IS NOT NULL AND voided_at IS NULL "
            "AND void_reason IS NULL) OR (status = 'void' AND voided_at IS NOT NULL "
            "AND btrim(void_reason) <> '')",
            name="ck_quotations_lifecycle_times",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_quotations_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_quotations_source_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quotations"),
        sa.UniqueConstraint("organization_id", "id", name="uq_quotations_organization_id_id"),
    )
    op.create_index(
        "uq_quotations_organization_document_number",
        "quotations",
        ["organization_id", "document_number"],
        unique=True,
    )
    op.create_index(
        "ix_quotations_organization_date_status",
        "quotations",
        ["organization_id", "quotation_date", "status", "id"],
    )
    op.create_table(
        "quotation_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("size", sa.String(200), nullable=True),
        sa.Column("paper", sa.String(200), nullable=True),
        sa.Column("color", sa.String(100), nullable=True),
        sa.Column("coating", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("plate_fee", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("die_fee", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("line_number >= 1", name="ck_quotation_items_line_positive"),
        sa.CheckConstraint("btrim(product_name) <> ''", name="ck_quotation_items_product_nonblank"),
        sa.CheckConstraint("quantity > 0", name="ck_quotation_items_quantity_positive"),
        sa.CheckConstraint(
            "unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0",
            name="ck_quotation_items_money_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_quotation_items_quotation_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quotation_items"),
        sa.UniqueConstraint("quotation_id", "line_number", name="uq_quotation_items_line"),
    )
    op.create_index(
        "ix_quotation_items_organization_quotation",
        "quotation_items",
        ["organization_id", "quotation_id", "line_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_quotation_items_organization_quotation", table_name="quotation_items")
    op.drop_table("quotation_items")
    op.drop_index("ix_quotations_organization_date_status", table_name="quotations")
    op.drop_index("uq_quotations_organization_document_number", table_name="quotations")
    op.drop_table("quotations")
