"""Single-item work order with company PDF form snapshots."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
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


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'confirmed', 'void')", name="ck_work_orders_status"),
        CheckConstraint("btrim(document_number) <> ''", name="ck_work_orders_number_nonblank"),
        CheckConstraint("btrim(product_name) <> ''", name="ck_work_orders_product_nonblank"),
        CheckConstraint("order_quantity > 0", name="ck_work_orders_quantity_positive"),
        CheckConstraint(
            "unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0",
            name="ck_work_orders_money_nonnegative",
        ),
        CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND voided_at IS NULL AND void_reason IS NULL) "
            "OR (status = 'confirmed' AND confirmed_at IS NOT NULL AND voided_at IS NULL AND void_reason IS NULL) "
            "OR (status = 'void' AND voided_at IS NOT NULL AND btrim(void_reason) <> '')",
            name="ck_work_orders_lifecycle",
        ),
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            ["production_cases.organization_id", "production_cases.id"],
            name="fk_work_orders_case_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_work_orders_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_quotation_item_id"],
            ["quotation_items.organization_id", "quotation_items.id"],
            name="fk_work_orders_quote_item_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_work_orders_source_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_work_orders_org_id"),
        Index("uq_work_orders_org_number", "organization_id", "document_number", unique=True),
        Index(
            "uq_work_orders_org_quote_item",
            "organization_id",
            "source_quotation_item_id",
            unique=True,
            postgresql_where=text("source_quotation_item_id IS NOT NULL"),
        ),
        Index("ix_work_orders_org_case", "organization_id", "case_id", "document_number"),
        Index("ix_work_orders_org_due_status", "organization_id", "delivery_date", "status", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    case_id: Mapped[UUID]
    document_number: Mapped[str] = mapped_column(String(32))
    order_date: Mapped[date] = mapped_column(Date)
    delivery_date: Mapped[date | None] = mapped_column(Date)
    customer_id: Mapped[UUID]
    customer_order_number: Mapped[str | None] = mapped_column(String(100))
    organization_snapshot: Mapped[dict] = mapped_column(JSON)
    customer_snapshot: Mapped[dict] = mapped_column(JSON)
    product_name: Mapped[str] = mapped_column(String(500))
    order_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    specification: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    plate_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    die_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    papers: Mapped[list] = mapped_column(JSON)
    print_specification: Mapped[dict] = mapped_column(JSON)
    processes: Mapped[list] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    source_quotation_item_id: Mapped[UUID | None]
    source_work_order_id: Mapped[UUID | None]
    legacy_document_number: Mapped[str | None] = mapped_column(String(128))
    legacy_source_table: Mapped[str | None] = mapped_column(String(64))
    legacy_source_key: Mapped[str | None] = mapped_column(String(128))
    document_snapshot: Mapped[dict | None] = mapped_column(JSON)
    print_metadata: Mapped[dict | None] = mapped_column(JSON)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
