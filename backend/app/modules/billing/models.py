"""Organization-scoped statements, receipts, and allocation ledgers."""

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


class Statement(Base):
    __tablename__ = "statements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','issued','partially_paid','paid','cancelled')",
            name="ck_statements_status",
        ),
        CheckConstraint("period_from <= period_to", name="ck_statements_period"),
        CheckConstraint("version > 0", name="ck_statements_version"),
        CheckConstraint(
            "subtotal_before_rounding >= 0 AND subtotal >= 0 AND tax_amount >= 0 AND grand_total >= 0",
            name="ck_statements_amounts",
        ),
        CheckConstraint(
            "rounding_scope IS NULL OR rounding_scope IN ('per_line','grand_total')",
            name="ck_statements_rounding_scope",
        ),
        CheckConstraint(
            "rounding_decimal_places IS NULL OR rounding_decimal_places BETWEEN 0 AND 4",
            name="ck_statements_rounding_places",
        ),
        CheckConstraint(
            "(tax_enabled = false AND tax_rate_percent IS NULL AND rounding_scope IS NULL AND rounding_decimal_places IS NULL AND tax_amount = 0) OR (tax_enabled = true AND tax_rate_percent > 0 AND tax_rate_percent <= 100 AND rounding_scope IS NOT NULL AND rounding_decimal_places IS NOT NULL)",
            name="ck_statements_tax_policy",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_statements_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_statements_creator_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_statements_org_id"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_statements_idempotency"),
        Index("uq_statements_org_number", "organization_id", "document_number", unique=True),
        Index(
            "uq_statements_org_issue_key",
            "organization_id",
            "issue_idempotency_key",
            unique=True,
            postgresql_where=text("issue_idempotency_key IS NOT NULL"),
        ),
        Index(
            "uq_statements_org_cancel_key",
            "organization_id",
            "cancellation_idempotency_key",
            unique=True,
            postgresql_where=text("cancellation_idempotency_key IS NOT NULL"),
        ),
        Index("ix_statements_org_date_status", "organization_id", "statement_date", "status", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    document_number: Mapped[str] = mapped_column(String(32))
    statement_date: Mapped[date] = mapped_column(Date)
    period_from: Mapped[date] = mapped_column(Date)
    period_to: Mapped[date] = mapped_column(Date)
    customer_id: Mapped[UUID]
    customer_snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    tax_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    tax_rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    rounding_scope: Mapped[str | None] = mapped_column(String(16))
    rounding_decimal_places: Mapped[int | None]
    subtotal_before_rounding: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    rounding_adjustment: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[UUID]
    issue_idempotency_key: Mapped[UUID | None]
    cancellation_idempotency_key: Mapped[UUID | None]
    legacy_document_number: Mapped[str | None] = mapped_column(String(128))
    document_snapshot: Mapped[dict | None] = mapped_column(JSON)
    created_by_membership_id: Mapped[UUID]
    created_by_user_id: Mapped[UUID]
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StatementItem(Base):
    __tablename__ = "statement_items"
    __table_args__ = (
        CheckConstraint("line_no > 0 AND amount >= 0", name="ck_statement_items_values"),
        CheckConstraint("btrim(content) <> ''", name="ck_statement_items_content"),
        ForeignKeyConstraint(
            ["organization_id", "statement_id"],
            ["statements.organization_id", "statements.id"],
            name="fk_statement_items_statement_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_pricing_item_id"],
            ["pricing_items.organization_id", "pricing_items.id"],
            name="fk_statement_items_pricing_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_pricing_document_id"],
            ["pricing_documents.organization_id", "pricing_documents.id"],
            name="fk_statement_items_pricing_document_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_statement_items_org_id"),
        UniqueConstraint(
            "organization_id", "statement_id", "line_no", name="uq_statement_items_line"
        ),
        Index(
            "uq_statement_items_active_source",
            "organization_id",
            "source_pricing_item_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    statement_id: Mapped[UUID]
    source_pricing_item_id: Mapped[UUID]
    source_pricing_document_id: Mapped[UUID]
    line_no: Mapped[int]
    content: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    plate_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    die_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    source_snapshot: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint("status IN ('confirmed','reversed')", name="ck_receipts_status"),
        CheckConstraint("amount > 0", name="ck_receipts_amount"),
        CheckConstraint("btrim(payment_method) <> ''", name="ck_receipts_method"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_receipts_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_receipts_creator_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_receipts_org_id"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_receipts_idempotency"),
        Index("uq_receipts_org_number", "organization_id", "document_number", unique=True),
        Index(
            "uq_receipts_org_reverse_key",
            "organization_id",
            "reversal_idempotency_key",
            unique=True,
            postgresql_where=text("reversal_idempotency_key IS NOT NULL"),
        ),
        Index("ix_receipts_org_date_status", "organization_id", "receipt_date", "status", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    document_number: Mapped[str] = mapped_column(String(32))
    receipt_date: Mapped[date]
    customer_id: Mapped[UUID]
    customer_snapshot: Mapped[dict] = mapped_column(JSON)
    payment_method: Mapped[str] = mapped_column(String(64))
    reference_number: Mapped[str | None] = mapped_column(String(128))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    status: Mapped[str] = mapped_column(String(16), default="confirmed", server_default="confirmed")
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[UUID]
    reversal_idempotency_key: Mapped[UUID | None]
    legacy_document_number: Mapped[str | None] = mapped_column(String(128))
    created_by_membership_id: Mapped[UUID]
    created_by_user_id: Mapped[UUID]
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReceiptAllocation(Base):
    __tablename__ = "receipt_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_receipt_allocations_amount"),
        ForeignKeyConstraint(
            ["organization_id", "receipt_id"],
            ["receipts.organization_id", "receipts.id"],
            name="fk_receipt_allocations_receipt_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "statement_id"],
            ["statements.organization_id", "statements.id"],
            name="fk_receipt_allocations_statement_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id", "receipt_id", "statement_id", name="uq_receipt_allocations_pair"
        ),
        Index(
            "ix_receipt_allocations_statement_active",
            "organization_id",
            "statement_id",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    receipt_id: Mapped[UUID]
    statement_id: Mapped[UUID]
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
