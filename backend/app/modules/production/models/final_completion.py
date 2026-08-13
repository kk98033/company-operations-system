"""Append-only final completion or full reversal."""

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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinalCompletionEntry(Base):
    __tablename__ = "final_completion_entries"
    __table_args__ = (
        CheckConstraint("entry_type IN ('completion','reversal')", name="ck_final_completion_type"),
        CheckConstraint(
            "source_type IN ('manual','shipment_completion','legacy')",
            name="ck_final_completion_source",
        ),
        CheckConstraint(
            "(entry_type = 'completion' AND quantity > 0 AND reversal_of_id IS NULL AND transport_process_event_id IS NOT NULL) OR (entry_type = 'reversal' AND quantity < 0 AND reversal_of_id IS NOT NULL AND transport_process_event_id IS NULL)",
            name="ck_final_completion_shape",
        ),
        CheckConstraint("btrim(reason) <> ''", name="ck_final_completion_reason"),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_final_completion_order_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id", "transport_process_event_id"],
            [
                "process_events.organization_id",
                "process_events.work_order_id",
                "process_events.id",
            ],
            name="fk_final_completion_transport_event",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "reversal_of_id"],
            ["final_completion_entries.organization_id", "final_completion_entries.id"],
            name="fk_final_completion_reversal",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_final_completion_actor_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_final_completion_org_id"),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_final_completion_idempotency"
        ),
        Index(
            "uq_final_completion_reversal_once",
            "organization_id",
            "reversal_of_id",
            unique=True,
            postgresql_where=text("reversal_of_id IS NOT NULL"),
        ),
        Index(
            "ix_final_completion_order_created", "organization_id", "work_order_id", "created_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    work_order_id: Mapped[UUID]
    entry_type: Mapped[str] = mapped_column(String(16))
    source_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    transport_process_event_id: Mapped[UUID | None]
    reversal_of_id: Mapped[UUID | None]
    correlation_id: Mapped[UUID]
    idempotency_key: Mapped[UUID]
    reason: Mapped[str] = mapped_column(Text)
    actor_membership_id: Mapped[UUID]
    actor_user_id: Mapped[UUID]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
