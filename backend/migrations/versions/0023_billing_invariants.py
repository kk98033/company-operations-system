"""Protect billing allocation totals and immutable ledgers.

Revision ID: 0023_billing_invariants
Revises: 0022_billing
Create Date: 2026-08-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023_billing_invariants"
down_revision: str | Sequence[str] | None = "0022_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION validate_receipt_allocation_insert()
        RETURNS trigger AS $$
        DECLARE
            receipt_total numeric(18,4);
            receipt_customer uuid;
            statement_total numeric(18,4);
            statement_customer uuid;
            receipt_allocated numeric(18,4);
            statement_paid numeric(18,4);
        BEGIN
            SELECT amount, customer_id
              INTO receipt_total, receipt_customer
              FROM receipts
             WHERE organization_id = NEW.organization_id
               AND id = NEW.receipt_id
               AND status = 'confirmed'
             FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'billing receipt is not active';
            END IF;

            SELECT grand_total, customer_id
              INTO statement_total, statement_customer
              FROM statements
             WHERE organization_id = NEW.organization_id
               AND id = NEW.statement_id
               AND status IN ('issued', 'partially_paid')
             FOR UPDATE;
            IF NOT FOUND OR receipt_customer <> statement_customer THEN
                RAISE EXCEPTION 'billing statement is not allocatable';
            END IF;

            SELECT COALESCE(SUM(amount), 0)
              INTO receipt_allocated
              FROM receipt_allocations
             WHERE organization_id = NEW.organization_id
               AND receipt_id = NEW.receipt_id
               AND is_active;
            IF receipt_allocated + NEW.amount > receipt_total THEN
                RAISE EXCEPTION 'receipt allocation exceeds receipt amount';
            END IF;

            SELECT COALESCE(SUM(allocation.amount), 0)
              INTO statement_paid
              FROM receipt_allocations allocation
              JOIN receipts receipt
                ON receipt.organization_id = allocation.organization_id
               AND receipt.id = allocation.receipt_id
               AND receipt.status = 'confirmed'
             WHERE allocation.organization_id = NEW.organization_id
               AND allocation.statement_id = NEW.statement_id
               AND allocation.is_active;
            IF statement_paid + NEW.amount > statement_total THEN
                RAISE EXCEPTION 'receipt allocation exceeds statement balance';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_receipt_allocation_validate_insert
        BEFORE INSERT ON receipt_allocations
        FOR EACH ROW EXECUTE FUNCTION validate_receipt_allocation_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_receipt_allocation_mutation()
        RETURNS trigger AS $$
        DECLARE parent_status text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'receipt allocations are immutable';
            END IF;
            SELECT status INTO parent_status
              FROM receipts
             WHERE organization_id = OLD.organization_id AND id = OLD.receipt_id;
            IF OLD.is_active
               AND NOT NEW.is_active
               AND parent_status = 'reversed'
               AND (to_jsonb(NEW) - 'is_active') = (to_jsonb(OLD) - 'is_active') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'receipt allocations are immutable';
        END;
        $$ LANGUAGE plpgsql;

        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_receipt_allocation_guard_mutation
        BEFORE UPDATE OR DELETE ON receipt_allocations
        FOR EACH ROW EXECUTE FUNCTION guard_receipt_allocation_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION guard_statement_item_mutation()
        RETURNS trigger AS $$
        DECLARE parent_status text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'statement items are immutable';
            END IF;
            SELECT status INTO parent_status
              FROM statements
             WHERE organization_id = OLD.organization_id AND id = OLD.statement_id;
            IF OLD.is_active
               AND NOT NEW.is_active
               AND parent_status = 'cancelled'
               AND (to_jsonb(NEW) - 'is_active') = (to_jsonb(OLD) - 'is_active') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'statement items are immutable';
        END;
        $$ LANGUAGE plpgsql;

        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_statement_item_guard_mutation
        BEFORE UPDATE OR DELETE ON statement_items
        FOR EACH ROW EXECUTE FUNCTION guard_statement_item_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_statement_item_guard_mutation ON statement_items")
    op.execute("DROP FUNCTION guard_statement_item_mutation()")
    op.execute("DROP TRIGGER trg_receipt_allocation_guard_mutation ON receipt_allocations")
    op.execute("DROP FUNCTION guard_receipt_allocation_mutation()")
    op.execute("DROP TRIGGER trg_receipt_allocation_validate_insert ON receipt_allocations")
    op.execute("DROP FUNCTION validate_receipt_allocation_insert()")
