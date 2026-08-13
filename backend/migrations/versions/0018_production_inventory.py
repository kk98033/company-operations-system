"""Create append-only production, completion, and inventory ledgers.

Revision ID: 0018_production_inventory
Revises: 0017_work_orders
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_production_inventory"
down_revision: str | Sequence[str] | None = "0017_work_orders"
branch_labels = None
depends_on = None


def _actor_fk(name: str, member: str, user: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id", member, user],
        [
            "organization_members.organization_id",
            "organization_members.id",
            "organization_members.user_id",
        ],
        name=name,
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.create_table(
        "process_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("process_code", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("completed_quantity", sa.Numeric(14, 4), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "process_code IN ('artwork','output','plate','proof','printing','coating','mounting','die','die_cutting','finishing','gluing','transport','other')",
            name="ck_process_events_code",
        ),
        sa.CheckConstraint(
            "event_type IN ('start','partial_complete','complete','reopen')",
            name="ck_process_events_type",
        ),
        sa.CheckConstraint("sequence_no > 0", name="ck_process_events_sequence"),
        sa.CheckConstraint(
            "(event_type = 'partial_complete' AND completed_quantity > 0) OR (event_type <> 'partial_complete' AND completed_quantity IS NULL)",
            name="ck_process_events_partial_quantity",
        ),
        sa.CheckConstraint(
            "(event_type = 'reopen' AND reason IS NOT NULL AND btrim(reason) <> '') OR event_type <> 'reopen'",
            name="ck_process_events_reopen_reason",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_process_events_work_order_scope",
            ondelete="RESTRICT",
        ),
        _actor_fk("fk_process_events_actor_scope", "actor_membership_id", "actor_user_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_process_events_org_id"),
        sa.UniqueConstraint(
            "organization_id",
            "work_order_id",
            "process_code",
            "sequence_no",
            name="uq_process_events_sequence",
        ),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_process_events_idempotency"
        ),
    )
    op.create_index(
        "ix_process_events_order_process",
        "process_events",
        ["organization_id", "work_order_id", "process_code", "sequence_no"],
    )

    op.create_table(
        "final_completion_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(16), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("transport_process_event_id", sa.Uuid(), nullable=True),
        sa.Column("reversal_of_id", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "entry_type IN ('completion','reversal')", name="ck_final_completion_type"
        ),
        sa.CheckConstraint(
            "source_type IN ('manual','shipment_completion','legacy')",
            name="ck_final_completion_source",
        ),
        sa.CheckConstraint(
            "(entry_type = 'completion' AND quantity > 0 AND reversal_of_id IS NULL AND transport_process_event_id IS NOT NULL) OR (entry_type = 'reversal' AND quantity < 0 AND reversal_of_id IS NOT NULL AND transport_process_event_id IS NULL)",
            name="ck_final_completion_shape",
        ),
        sa.CheckConstraint("btrim(reason) <> ''", name="ck_final_completion_reason"),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_final_completion_order_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "transport_process_event_id"],
            ["process_events.organization_id", "process_events.id"],
            name="fk_final_completion_transport_event",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "reversal_of_id"],
            ["final_completion_entries.organization_id", "final_completion_entries.id"],
            name="fk_final_completion_reversal",
            ondelete="RESTRICT",
        ),
        _actor_fk("fk_final_completion_actor_scope", "actor_membership_id", "actor_user_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_final_completion_org_id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_final_completion_idempotency"
        ),
    )
    op.create_index(
        "uq_final_completion_reversal_once",
        "final_completion_entries",
        ["organization_id", "reversal_of_id"],
        unique=True,
        postgresql_where=sa.text("reversal_of_id IS NOT NULL"),
    )
    op.create_index(
        "ix_final_completion_order_created",
        "final_completion_entries",
        ["organization_id", "work_order_id", "created_at"],
    )

    op.create_table(
        "inventory_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("approved_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("quantity <> 0", name="ck_inventory_adjustments_nonzero"),
        sa.CheckConstraint("btrim(reason) <> ''", name="ck_inventory_adjustments_reason"),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_inventory_adjustments_order_scope",
            ondelete="RESTRICT",
        ),
        _actor_fk(
            "fk_inventory_adjustments_approver_scope",
            "approved_by_membership_id",
            "approved_by_user_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_inventory_adjustments_org_id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_inventory_adjustments_idempotency"
        ),
    )
    op.create_index(
        "ix_inventory_adjustments_order_created",
        "inventory_adjustments",
        ["organization_id", "work_order_id", "created_at"],
    )

    op.create_table(
        "inventory_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("final_completion_entry_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_adjustment_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("quantity <> 0", name="ck_inventory_ledger_nonzero"),
        sa.CheckConstraint(
            "event_type IN ('final_completion','completion_reversal','manual_adjustment')",
            name="ck_inventory_ledger_type",
        ),
        sa.CheckConstraint(
            "(final_completion_entry_id IS NOT NULL)::int + (inventory_adjustment_id IS NOT NULL)::int = 1",
            name="ck_inventory_ledger_one_source",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_inventory_ledger_order_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "final_completion_entry_id"],
            ["final_completion_entries.organization_id", "final_completion_entries.id"],
            name="fk_inventory_ledger_completion_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "inventory_adjustment_id"],
            ["inventory_adjustments.organization_id", "inventory_adjustments.id"],
            name="fk_inventory_ledger_adjustment_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "final_completion_entry_id", name="uq_inventory_ledger_completion"
        ),
        sa.UniqueConstraint(
            "organization_id", "inventory_adjustment_id", name="uq_inventory_ledger_adjustment"
        ),
    )
    op.create_index(
        "ix_inventory_ledger_order_created",
        "inventory_ledger",
        ["organization_id", "work_order_id", "created_at", "id"],
    )

    op.execute("""
        CREATE FUNCTION reject_phase5_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'phase 5 ledger rows are append-only'; END;
        $$ LANGUAGE plpgsql;
    """)
    for table in (
        "process_events",
        "final_completion_entries",
        "inventory_adjustments",
        "inventory_ledger",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_phase5_mutation()"
        )


def downgrade() -> None:
    op.drop_table("inventory_ledger")
    op.drop_table("inventory_adjustments")
    op.drop_table("final_completion_entries")
    op.drop_table("process_events")
    op.execute("DROP FUNCTION reject_phase5_mutation()")
