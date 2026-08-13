"""Append-only work-order process transition."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessEvent(Base):
    __tablename__ = "process_events"
    __table_args__ = (
        CheckConstraint(
            "process_code IN ('artwork','output','plate','proof','printing','coating','mounting','die','die_cutting','finishing','gluing','transport','other')",
            name="ck_process_events_code",
        ),
        CheckConstraint(
            "event_type IN ('start','partial_complete','complete','reopen')",
            name="ck_process_events_type",
        ),
        CheckConstraint("sequence_no > 0", name="ck_process_events_sequence"),
        CheckConstraint(
            "(event_type = 'partial_complete' AND completed_quantity > 0) OR (event_type <> 'partial_complete' AND completed_quantity IS NULL)",
            name="ck_process_events_partial_quantity",
        ),
        CheckConstraint(
            "(event_type = 'reopen' AND reason IS NOT NULL AND btrim(reason) <> '') OR event_type <> 'reopen'",
            name="ck_process_events_reopen_reason",
        ),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_process_events_work_order_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_process_events_actor_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_process_events_org_id"),
        UniqueConstraint(
            "organization_id",
            "work_order_id",
            "id",
            name="uq_process_events_org_order_id",
        ),
        UniqueConstraint(
            "organization_id",
            "work_order_id",
            "process_code",
            "sequence_no",
            name="uq_process_events_sequence",
        ),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_process_events_idempotency"
        ),
        Index(
            "ix_process_events_order_process",
            "organization_id",
            "work_order_id",
            "process_code",
            "sequence_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    work_order_id: Mapped[UUID]
    process_code: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(32))
    sequence_no: Mapped[int] = mapped_column(Integer)
    completed_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[UUID]
    actor_membership_id: Mapped[UUID]
    actor_user_id: Mapped[UUID]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
