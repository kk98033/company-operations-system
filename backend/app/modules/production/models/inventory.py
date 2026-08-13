"""Approved inventory adjustments and immutable quantity ledger."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"
    __table_args__ = (
        CheckConstraint("quantity <> 0", name="ck_inventory_adjustments_nonzero"),
        CheckConstraint("btrim(reason) <> ''", name="ck_inventory_adjustments_reason"),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_inventory_adjustments_order_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "approved_by_membership_id", "approved_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_inventory_adjustments_approver_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_inventory_adjustments_org_id"),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_inventory_adjustments_idempotency"
        ),
        Index(
            "ix_inventory_adjustments_order_created",
            "organization_id",
            "work_order_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    work_order_id: Mapped[UUID]
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    reason: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[UUID]
    approved_by_membership_id: Mapped[UUID]
    approved_by_user_id: Mapped[UUID]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryLedgerEntry(Base):
    __tablename__ = "inventory_ledger"
    __table_args__ = (
        CheckConstraint("quantity <> 0", name="ck_inventory_ledger_nonzero"),
        CheckConstraint(
            "event_type IN ('final_completion','completion_reversal','manual_adjustment')",
            name="ck_inventory_ledger_type",
        ),
        CheckConstraint(
            "(final_completion_entry_id IS NOT NULL)::int + (inventory_adjustment_id IS NOT NULL)::int = 1",
            name="ck_inventory_ledger_one_source",
        ),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_inventory_ledger_order_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "final_completion_entry_id"],
            ["final_completion_entries.organization_id", "final_completion_entries.id"],
            name="fk_inventory_ledger_completion_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "inventory_adjustment_id"],
            ["inventory_adjustments.organization_id", "inventory_adjustments.id"],
            name="fk_inventory_ledger_adjustment_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id", "final_completion_entry_id", name="uq_inventory_ledger_completion"
        ),
        UniqueConstraint(
            "organization_id", "inventory_adjustment_id", name="uq_inventory_ledger_adjustment"
        ),
        Index(
            "ix_inventory_ledger_order_created",
            "organization_id",
            "work_order_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    work_order_id: Mapped[UUID]
    event_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    final_completion_entry_id: Mapped[UUID | None]
    inventory_adjustment_id: Mapped[UUID | None]
    reason: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
