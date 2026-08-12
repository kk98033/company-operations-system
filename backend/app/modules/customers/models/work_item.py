"""Reusable customer work-item specification."""

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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomerWorkItem(Base):
    __tablename__ = "customer_work_items"
    __table_args__ = (
        CheckConstraint("btrim(code) <> ''", name="ck_customer_work_items_code_nonblank"),
        CheckConstraint("btrim(name) <> ''", name="ck_customer_work_items_name_nonblank"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_customer_work_items_status_allowed"),
        CheckConstraint("source IN ('manual', 'legacy', 'work_order')", name="ck_customer_work_items_source_allowed"),
        CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="ck_customer_work_items_unit_price_nonnegative"),
        CheckConstraint("(legacy_source_table IS NULL) = (legacy_source_key IS NULL)", name="ck_customer_work_items_legacy_source_pair"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_customer_work_items_customer_scope",
            ondelete="RESTRICT",
        ),
        Index("uq_customer_work_items_customer_normalized_code", "organization_id", "customer_id", text("lower(btrim(code))"), unique=True),
        Index("ix_customer_work_items_customer_status_name", "organization_id", "customer_id", "status", "name", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    customer_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    specification: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    source: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")
    source_reference: Mapped[str | None] = mapped_column(String(128))
    legacy_source_table: Mapped[str | None] = mapped_column(String(64))
    legacy_source_key: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
