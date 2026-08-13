"""Organization-scoped shipment documents and immutable line snapshots."""

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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint("status IN ('draft','confirmed','cancelled')", name="ck_shipments_status"),
        CheckConstraint("btrim(document_number) <> ''", name="ck_shipments_number"),
        CheckConstraint("version > 0", name="ck_shipments_version"),
        CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status = 'cancelled' AND confirmed_at IS NOT NULL AND cancelled_at IS NOT NULL AND btrim(cancel_reason) <> '')",
            name="ck_shipments_lifecycle",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_shipments_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_shipments_creator_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_shipments_org_id"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_shipments_idempotency"),
        Index("uq_shipments_org_number", "organization_id", "document_number", unique=True),
        Index(
            "uq_shipments_org_confirmation_key",
            "organization_id",
            "confirmation_idempotency_key",
            unique=True,
            postgresql_where=text("confirmation_idempotency_key IS NOT NULL"),
        ),
        Index(
            "uq_shipments_org_cancellation_key",
            "organization_id",
            "cancellation_idempotency_key",
            unique=True,
            postgresql_where=text("cancellation_idempotency_key IS NOT NULL"),
        ),
        Index("ix_shipments_org_date_status", "organization_id", "shipment_date", "status", "id"),
        Index(
            "uq_shipments_org_legacy_source",
            "organization_id",
            "legacy_source_table",
            "legacy_source_key",
            unique=True,
            postgresql_where=text("legacy_source_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    document_number: Mapped[str] = mapped_column(String(32))
    shipment_date: Mapped[date] = mapped_column(Date)
    customer_id: Mapped[UUID]
    customer_snapshot: Mapped[dict] = mapped_column(JSON)
    delivery_address_snapshot: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    idempotency_key: Mapped[UUID]
    confirmation_idempotency_key: Mapped[UUID | None]
    cancellation_idempotency_key: Mapped[UUID | None]
    correlation_id: Mapped[UUID]
    legacy_document_number: Mapped[str | None] = mapped_column(String(128))
    legacy_source_table: Mapped[str | None] = mapped_column(String(64))
    legacy_source_key: Mapped[str | None] = mapped_column(String(128))
    document_snapshot: Mapped[dict | None] = mapped_column(JSON)
    created_by_membership_id: Mapped[UUID]
    created_by_user_id: Mapped[UUID]
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShipmentItem(Base):
    __tablename__ = "shipment_items"
    __table_args__ = (
        CheckConstraint("line_no > 0", name="ck_shipment_items_line"),
        CheckConstraint(
            "delivered_quantity >= 0 AND spare_quantity >= 0", name="ck_shipment_items_quantities"
        ),
        CheckConstraint(
            "inventory_consumed_quantity = delivered_quantity + spare_quantity AND inventory_consumed_quantity > 0",
            name="ck_shipment_items_consumed",
        ),
        ForeignKeyConstraint(
            ["organization_id", "shipment_id"],
            ["shipments.organization_id", "shipments.id"],
            name="fk_shipment_items_shipment_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_shipment_items_order_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_shipment_items_org_id"),
        UniqueConstraint(
            "organization_id", "shipment_id", "line_no", name="uq_shipment_items_line"
        ),
        UniqueConstraint(
            "organization_id", "shipment_id", "work_order_id", name="uq_shipment_items_order"
        ),
        Index("ix_shipment_items_order", "organization_id", "work_order_id", "shipment_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    shipment_id: Mapped[UUID]
    work_order_id: Mapped[UUID]
    line_no: Mapped[int] = mapped_column(Integer)
    work_order_document_number: Mapped[str] = mapped_column(String(32))
    customer_order_number: Mapped[str | None] = mapped_column(String(100))
    product_name: Mapped[str] = mapped_column(String(500))
    specification: Mapped[str | None] = mapped_column(Text)
    delivered_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    spare_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    inventory_consumed_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    available_quantity_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    cumulative_delivered_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
