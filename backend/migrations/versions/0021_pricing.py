"""Create pricing documents, items, and price history.

Revision ID: 0021_pricing
Revises: 0020_shipments
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_pricing"
down_revision: str | Sequence[str] | None = "0020_shipments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pricing_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(32), nullable=False),
        sa.Column("pricing_date", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("confirmation_idempotency_key", sa.Uuid()),
        sa.Column("cancellation_idempotency_key", sa.Uuid()),
        sa.Column("reopen_idempotency_key", sa.Uuid()),
        sa.Column("legacy_document_number", sa.String(128)),
        sa.Column("legacy_source_table", sa.String(64)),
        sa.Column("legacy_source_key", sa.String(128)),
        sa.Column("document_snapshot", sa.JSON()),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft','confirmed','cancelled')", name="ck_pricing_documents_status"
        ),
        sa.CheckConstraint("btrim(document_number) <> ''", name="ck_pricing_documents_number"),
        sa.CheckConstraint("version > 0", name="ck_pricing_documents_version"),
        sa.CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR (status = 'confirmed' AND confirmed_at IS NOT NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR (status = 'cancelled' AND confirmed_at IS NOT NULL AND cancelled_at IS NOT NULL AND btrim(cancel_reason) <> '')",
            name="ck_pricing_documents_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_pricing_documents_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_pricing_documents_creator_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_pricing_documents_org_id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_pricing_documents_idempotency"
        ),
    )
    op.create_index(
        "uq_pricing_documents_org_number",
        "pricing_documents",
        ["organization_id", "document_number"],
        unique=True,
    )
    op.create_index(
        "uq_pricing_documents_org_confirm_key",
        "pricing_documents",
        ["organization_id", "confirmation_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("confirmation_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "uq_pricing_documents_org_cancel_key",
        "pricing_documents",
        ["organization_id", "cancellation_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("cancellation_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "uq_pricing_documents_org_reopen_key",
        "pricing_documents",
        ["organization_id", "reopen_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("reopen_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "ix_pricing_documents_org_date_status",
        "pricing_documents",
        ["organization_id", "pricing_date", "status", "id"],
    )
    op.create_index(
        "uq_pricing_documents_org_legacy_source",
        "pricing_documents",
        ["organization_id", "legacy_source_table", "legacy_source_key"],
        unique=True,
        postgresql_where=sa.text("legacy_source_key IS NOT NULL"),
    )
    op.create_table(
        "pricing_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("pricing_document_id", sa.Uuid(), nullable=False),
        sa.Column("source_shipment_item_id", sa.Uuid()),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(16), nullable=False),
        sa.Column("content", sa.String(500), nullable=False),
        sa.Column("product_name", sa.String(500)),
        sa.Column("specification", sa.Text()),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("plate_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("die_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False),
        sa.Column("source_snapshot", sa.JSON()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("line_no > 0", name="ck_pricing_items_line"),
        sa.CheckConstraint("item_type IN ('base','spare','manual')", name="ck_pricing_items_type"),
        sa.CheckConstraint("btrim(content) <> ''", name="ck_pricing_items_content"),
        sa.CheckConstraint(
            "quantity >= 0 AND unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0",
            name="ck_pricing_items_amounts",
        ),
        sa.CheckConstraint(
            "subtotal = quantity * unit_price + plate_fee + die_fee",
            name="ck_pricing_items_subtotal",
        ),
        sa.CheckConstraint(
            "(item_type = 'manual' AND source_shipment_item_id IS NULL) OR (item_type IN ('base','spare') AND source_shipment_item_id IS NOT NULL)",
            name="ck_pricing_items_source",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "pricing_document_id"],
            ["pricing_documents.organization_id", "pricing_documents.id"],
            name="fk_pricing_items_document_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_shipment_item_id"],
            ["shipment_items.organization_id", "shipment_items.id"],
            name="fk_pricing_items_shipment_item_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_pricing_items_org_id"),
        sa.UniqueConstraint(
            "organization_id", "pricing_document_id", "line_no", name="uq_pricing_items_line"
        ),
    )
    op.create_index(
        "uq_pricing_items_base_source",
        "pricing_items",
        ["organization_id", "source_shipment_item_id"],
        unique=True,
        postgresql_where=sa.text("item_type = 'base' AND source_shipment_item_id IS NOT NULL"),
    )
    op.create_table(
        "price_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("source_pricing_item_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("specification", sa.Text()),
        sa.Column("specification_key", sa.String(500), server_default="", nullable=False),
        sa.Column("content", sa.String(500), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("plate_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("die_fee", sa.Numeric(14, 4), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("btrim(content) <> ''", name="ck_price_history_content"),
        sa.CheckConstraint(
            "unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0", name="ck_price_history_amounts"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_price_history_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_pricing_item_id"],
            ["pricing_items.organization_id", "pricing_items.id"],
            name="fk_price_history_pricing_item_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_history_suggestion",
        "price_history",
        ["organization_id", "customer_id", "product_name", "price_date"],
    )
    op.create_index(
        "uq_price_history_default",
        "price_history",
        ["organization_id", "customer_id", "product_name", "specification_key"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.execute(
        """CREATE FUNCTION protect_pricing_item_mutation() RETURNS trigger AS $$ BEGIN IF EXISTS (SELECT 1 FROM pricing_documents WHERE id = OLD.pricing_document_id AND organization_id = OLD.organization_id AND status <> 'draft') THEN RAISE EXCEPTION 'non-draft pricing items are immutable'; END IF; RETURN OLD; END; $$ LANGUAGE plpgsql;"""
    )
    op.execute(
        "CREATE TRIGGER trg_pricing_items_draft_only BEFORE UPDATE OR DELETE ON pricing_items FOR EACH ROW EXECUTE FUNCTION protect_pricing_item_mutation()"
    )
    op.execute(
        """CREATE FUNCTION protect_price_history_mutation() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'UPDATE' AND (to_jsonb(OLD) - 'is_default') = (to_jsonb(NEW) - 'is_default') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'price history is append-only except default selection';
        END;
        $$ LANGUAGE plpgsql;"""
    )
    op.execute(
        "CREATE TRIGGER trg_price_history_append_only BEFORE UPDATE OR DELETE ON price_history FOR EACH ROW EXECUTE FUNCTION protect_price_history_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_price_history_append_only ON price_history")
    op.execute("DROP FUNCTION protect_price_history_mutation()")
    op.execute("DROP TRIGGER trg_pricing_items_draft_only ON pricing_items")
    op.execute("DROP FUNCTION protect_pricing_item_mutation()")
    op.drop_table("price_history")
    op.drop_table("pricing_items")
    op.drop_table("pricing_documents")
