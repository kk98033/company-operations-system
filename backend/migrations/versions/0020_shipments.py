"""Create shipments and connect them to the immutable inventory ledger.

Revision ID: 0020_shipments
Revises: 0019_phase5_invariants
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_shipments"
down_revision: str | Sequence[str] | None = "0019_phase5_invariants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_number", sa.String(32), nullable=False),
        sa.Column("shipment_date", sa.Date(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("customer_snapshot", sa.JSON(), nullable=False),
        sa.Column("delivery_address_snapshot", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("confirmation_idempotency_key", sa.Uuid(), nullable=True),
        sa.Column("cancellation_idempotency_key", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("legacy_document_number", sa.String(128), nullable=True),
        sa.Column("legacy_source_table", sa.String(64), nullable=True),
        sa.Column("legacy_source_key", sa.String(128), nullable=True),
        sa.Column("document_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft','confirmed','cancelled')", name="ck_shipments_status"
        ),
        sa.CheckConstraint("btrim(document_number) <> ''", name="ck_shipments_number"),
        sa.CheckConstraint("version > 0", name="ck_shipments_version"),
        sa.CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status = 'cancelled' AND confirmed_at IS NOT NULL AND cancelled_at IS NOT NULL AND btrim(cancel_reason) <> '')",
            name="ck_shipments_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_shipments_customer_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_shipments_creator_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_shipments_org_id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_shipments_idempotency"),
    )
    op.create_index(
        "uq_shipments_org_number", "shipments", ["organization_id", "document_number"], unique=True
    )
    op.create_index(
        "uq_shipments_org_confirmation_key",
        "shipments",
        ["organization_id", "confirmation_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("confirmation_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "uq_shipments_org_cancellation_key",
        "shipments",
        ["organization_id", "cancellation_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("cancellation_idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "ix_shipments_org_date_status",
        "shipments",
        ["organization_id", "shipment_date", "status", "id"],
    )
    op.create_index(
        "uq_shipments_org_legacy_source",
        "shipments",
        ["organization_id", "legacy_source_table", "legacy_source_key"],
        unique=True,
        postgresql_where=sa.text("legacy_source_key IS NOT NULL"),
    )

    op.create_table(
        "shipment_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("work_order_document_number", sa.String(32), nullable=False),
        sa.Column("customer_order_number", sa.String(100), nullable=True),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("delivered_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("spare_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("inventory_consumed_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("available_quantity_snapshot", sa.Numeric(14, 4), nullable=True),
        sa.Column("cumulative_delivered_snapshot", sa.Numeric(14, 4), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("line_no > 0", name="ck_shipment_items_line"),
        sa.CheckConstraint(
            "delivered_quantity >= 0 AND spare_quantity >= 0", name="ck_shipment_items_quantities"
        ),
        sa.CheckConstraint(
            "inventory_consumed_quantity = delivered_quantity + spare_quantity AND inventory_consumed_quantity > 0",
            name="ck_shipment_items_consumed",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "shipment_id"],
            ["shipments.organization_id", "shipments.id"],
            name="fk_shipment_items_shipment_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_shipment_items_order_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_shipment_items_org_id"),
        sa.UniqueConstraint(
            "organization_id", "shipment_id", "line_no", name="uq_shipment_items_line"
        ),
        sa.UniqueConstraint(
            "organization_id", "shipment_id", "work_order_id", name="uq_shipment_items_order"
        ),
    )
    op.create_index(
        "ix_shipment_items_order",
        "shipment_items",
        ["organization_id", "work_order_id", "shipment_id"],
    )

    op.add_column("inventory_ledger", sa.Column("shipment_item_id", sa.Uuid(), nullable=True))
    op.drop_constraint("ck_inventory_ledger_type", "inventory_ledger", type_="check")
    op.drop_constraint("ck_inventory_ledger_one_source", "inventory_ledger", type_="check")
    op.create_check_constraint(
        "ck_inventory_ledger_type",
        "inventory_ledger",
        "event_type IN ('final_completion','completion_reversal','manual_adjustment','shipment_delivered','shipment_spare','shipment_reversal_delivered','shipment_reversal_spare')",
    )
    op.create_check_constraint(
        "ck_inventory_ledger_one_source",
        "inventory_ledger",
        "(final_completion_entry_id IS NOT NULL)::int + (inventory_adjustment_id IS NOT NULL)::int + (shipment_item_id IS NOT NULL)::int = 1",
    )
    op.create_foreign_key(
        "fk_inventory_ledger_shipment_item_scope",
        "inventory_ledger",
        "shipment_items",
        ["organization_id", "shipment_item_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_inventory_ledger_shipment_event",
        "inventory_ledger",
        ["organization_id", "shipment_item_id", "event_type"],
    )
    op.execute("""
        CREATE FUNCTION protect_shipment_item_mutation() RETURNS trigger AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM shipments WHERE id = OLD.shipment_id AND organization_id = OLD.organization_id AND status <> 'draft') THEN
                RAISE EXCEPTION 'confirmed shipment items are immutable';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute(
        "CREATE TRIGGER trg_shipment_items_draft_only BEFORE UPDATE OR DELETE ON shipment_items FOR EACH ROW EXECUTE FUNCTION protect_shipment_item_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_shipment_items_draft_only ON shipment_items")
    op.execute("DROP FUNCTION protect_shipment_item_mutation()")
    op.drop_constraint("uq_inventory_ledger_shipment_event", "inventory_ledger", type_="unique")
    op.drop_constraint(
        "fk_inventory_ledger_shipment_item_scope", "inventory_ledger", type_="foreignkey"
    )
    op.drop_constraint("ck_inventory_ledger_one_source", "inventory_ledger", type_="check")
    op.drop_constraint("ck_inventory_ledger_type", "inventory_ledger", type_="check")
    op.create_check_constraint(
        "ck_inventory_ledger_type",
        "inventory_ledger",
        "event_type IN ('final_completion','completion_reversal','manual_adjustment')",
    )
    op.create_check_constraint(
        "ck_inventory_ledger_one_source",
        "inventory_ledger",
        "(final_completion_entry_id IS NOT NULL)::int + (inventory_adjustment_id IS NOT NULL)::int = 1",
    )
    op.drop_column("inventory_ledger", "shipment_item_id")
    op.drop_table("shipment_items")
    op.drop_table("shipments")
