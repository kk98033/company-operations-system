"""Enforce final-completion and non-negative inventory invariants.

Revision ID: 0019_phase5_invariants
Revises: 0018_production_inventory
Create Date: 2026-08-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019_phase5_invariants"
down_revision: str | Sequence[str] | None = "0018_production_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_process_events_org_order_id",
        "process_events",
        ["organization_id", "work_order_id", "id"],
    )
    op.drop_constraint(
        "fk_final_completion_transport_event",
        "final_completion_entries",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_final_completion_transport_event",
        "final_completion_entries",
        "process_events",
        ["organization_id", "work_order_id", "transport_process_event_id"],
        ["organization_id", "work_order_id", "id"],
        ondelete="RESTRICT",
    )
    op.execute("""
        CREATE FUNCTION validate_final_completion_transport() RETURNS trigger AS $$
        BEGIN
            IF NEW.entry_type = 'completion' AND NOT EXISTS (
                SELECT 1 FROM process_events
                WHERE organization_id = NEW.organization_id
                  AND work_order_id = NEW.work_order_id
                  AND id = NEW.transport_process_event_id
                  AND process_code = 'transport'
                  AND event_type = 'complete'
            ) THEN
                RAISE EXCEPTION 'final completion requires a completed transport event';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_final_completion_transport
        BEFORE INSERT ON final_completion_entries
        FOR EACH ROW EXECUTE FUNCTION validate_final_completion_transport()
    """)
    op.execute("""
        CREATE FUNCTION validate_inventory_nonnegative() RETURNS trigger AS $$
        DECLARE current_balance numeric(14, 4);
        BEGIN
            PERFORM 1 FROM work_orders
            WHERE organization_id = NEW.organization_id AND id = NEW.work_order_id
            FOR UPDATE;
            SELECT COALESCE(SUM(quantity), 0) INTO current_balance
            FROM inventory_ledger
            WHERE organization_id = NEW.organization_id
              AND work_order_id = NEW.work_order_id;
            IF current_balance + NEW.quantity < 0 THEN
                RAISE EXCEPTION 'inventory balance cannot be negative';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_inventory_ledger_nonnegative
        BEFORE INSERT ON inventory_ledger
        FOR EACH ROW EXECUTE FUNCTION validate_inventory_nonnegative()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_inventory_ledger_nonnegative ON inventory_ledger")
    op.execute("DROP FUNCTION validate_inventory_nonnegative()")
    op.execute("DROP TRIGGER trg_final_completion_transport ON final_completion_entries")
    op.execute("DROP FUNCTION validate_final_completion_transport()")
    op.drop_constraint(
        "fk_final_completion_transport_event",
        "final_completion_entries",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_final_completion_transport_event",
        "final_completion_entries",
        "process_events",
        ["organization_id", "transport_process_event_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_process_events_org_order_id", "process_events", type_="unique")
