"""Organization-scoped pricing documents, items, and immutable price history."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
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


class PricingDocument(Base):
    __tablename__ = "pricing_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','confirmed','cancelled')", name="ck_pricing_documents_status"
        ),
        CheckConstraint("btrim(document_number) <> ''", name="ck_pricing_documents_number"),
        CheckConstraint("version > 0", name="ck_pricing_documents_version"),
        CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status = 'confirmed' AND confirmed_at IS NOT NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) OR "
            "(status = 'cancelled' AND confirmed_at IS NOT NULL AND cancelled_at IS NOT NULL AND btrim(cancel_reason) <> '')",
            name="ck_pricing_documents_lifecycle",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_pricing_documents_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_pricing_documents_creator_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_pricing_documents_org_id"),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_pricing_documents_idempotency"
        ),
        Index("uq_pricing_documents_org_number", "organization_id", "document_number", unique=True),
        Index(
            "uq_pricing_documents_org_confirm_key",
            "organization_id",
            "confirmation_idempotency_key",
            unique=True,
            postgresql_where=text("confirmation_idempotency_key IS NOT NULL"),
        ),
        Index(
            "uq_pricing_documents_org_cancel_key",
            "organization_id",
            "cancellation_idempotency_key",
            unique=True,
            postgresql_where=text("cancellation_idempotency_key IS NOT NULL"),
        ),
        Index(
            "uq_pricing_documents_org_reopen_key",
            "organization_id",
            "reopen_idempotency_key",
            unique=True,
            postgresql_where=text("reopen_idempotency_key IS NOT NULL"),
        ),
        Index(
            "ix_pricing_documents_org_date_status",
            "organization_id",
            "pricing_date",
            "status",
            "id",
        ),
        Index(
            "uq_pricing_documents_org_legacy_source",
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
    pricing_date: Mapped[date] = mapped_column(Date)
    customer_id: Mapped[UUID]
    customer_snapshot: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    idempotency_key: Mapped[UUID]
    confirmation_idempotency_key: Mapped[UUID | None]
    cancellation_idempotency_key: Mapped[UUID | None]
    reopen_idempotency_key: Mapped[UUID | None]
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


class PricingItem(Base):
    __tablename__ = "pricing_items"
    __table_args__ = (
        CheckConstraint("line_no > 0", name="ck_pricing_items_line"),
        CheckConstraint("item_type IN ('base','spare','manual')", name="ck_pricing_items_type"),
        CheckConstraint("btrim(content) <> ''", name="ck_pricing_items_content"),
        CheckConstraint(
            "quantity >= 0 AND unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0",
            name="ck_pricing_items_amounts",
        ),
        CheckConstraint(
            "subtotal = quantity * unit_price + plate_fee + die_fee",
            name="ck_pricing_items_subtotal",
        ),
        CheckConstraint(
            "(item_type = 'manual' AND source_shipment_item_id IS NULL) OR "
            "(item_type IN ('base','spare') AND source_shipment_item_id IS NOT NULL)",
            name="ck_pricing_items_source",
        ),
        ForeignKeyConstraint(
            ["organization_id", "pricing_document_id"],
            ["pricing_documents.organization_id", "pricing_documents.id"],
            name="fk_pricing_items_document_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_shipment_item_id"],
            ["shipment_items.organization_id", "shipment_items.id"],
            name="fk_pricing_items_shipment_item_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_pricing_items_org_id"),
        UniqueConstraint(
            "organization_id", "pricing_document_id", "line_no", name="uq_pricing_items_line"
        ),
        Index(
            "uq_pricing_items_base_source",
            "organization_id",
            "source_shipment_item_id",
            unique=True,
            postgresql_where=text("item_type = 'base' AND source_shipment_item_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    pricing_document_id: Mapped[UUID]
    source_shipment_item_id: Mapped[UUID | None]
    line_no: Mapped[int] = mapped_column(Integer)
    item_type: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(String(500))
    product_name: Mapped[str | None] = mapped_column(String(500))
    specification: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    plate_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    die_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    source_snapshot: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        CheckConstraint("btrim(content) <> ''", name="ck_price_history_content"),
        CheckConstraint(
            "unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0", name="ck_price_history_amounts"
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_price_history_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_pricing_item_id"],
            ["pricing_items.organization_id", "pricing_items.id"],
            name="fk_price_history_pricing_item_scope",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_price_history_suggestion",
            "organization_id",
            "customer_id",
            "product_name",
            "price_date",
        ),
        Index(
            "uq_price_history_default",
            "organization_id",
            "customer_id",
            "product_name",
            "specification_key",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    customer_id: Mapped[UUID]
    source_pricing_item_id: Mapped[UUID]
    product_name: Mapped[str] = mapped_column(String(500))
    specification: Mapped[str | None] = mapped_column(Text)
    specification_key: Mapped[str] = mapped_column(String(500), default="", server_default="")
    content: Mapped[str] = mapped_column(String(500))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    plate_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    die_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    price_date: Mapped[date] = mapped_column(Date)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
