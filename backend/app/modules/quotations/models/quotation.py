"""Quotation header with immutable organization and customer snapshots."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

JSON_TYPE = JSON()


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'void')", name="ck_quotations_status_allowed"
        ),
        CheckConstraint(
            "btrim(document_number) <> ''", name="ck_quotations_document_number_nonblank"
        ),
        CheckConstraint(
            "(legacy_source_table IS NULL) = (legacy_source_key IS NULL)",
            name="ck_quotations_legacy_source_pair",
        ),
        CheckConstraint(
            "(status = 'draft' AND confirmed_at IS NULL AND voided_at IS NULL AND void_reason IS NULL) "
            "OR (status = 'confirmed' AND confirmed_at IS NOT NULL AND voided_at IS NULL "
            "AND void_reason IS NULL) OR (status = 'void' AND voided_at IS NOT NULL "
            "AND btrim(void_reason) <> '')",
            name="ck_quotations_lifecycle_times",
        ),
        UniqueConstraint("organization_id", "id", name="uq_quotations_organization_id_id"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_quotations_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_quotations_source_scope",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_quotations_organization_document_number",
            "organization_id",
            "document_number",
            unique=True,
        ),
        Index(
            "ix_quotations_organization_date_status",
            "organization_id",
            "quotation_date",
            "status",
            "id",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    document_number: Mapped[str] = mapped_column(String(32))
    quotation_date: Mapped[date] = mapped_column(Date)
    customer_id: Mapped[UUID]
    organization_snapshot: Mapped[dict] = mapped_column(JSON_TYPE)
    customer_snapshot: Mapped[dict] = mapped_column(JSON_TYPE)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    source_quotation_id: Mapped[UUID | None]
    legacy_document_number: Mapped[str | None] = mapped_column(String(128))
    legacy_tax_included_raw: Mapped[str | None] = mapped_column(String(16))
    legacy_source_table: Mapped[str | None] = mapped_column(String(64))
    legacy_source_key: Mapped[str | None] = mapped_column(String(128))
    document_snapshot: Mapped[dict | None] = mapped_column(JSON_TYPE)
    print_metadata: Mapped[dict | None] = mapped_column(JSON_TYPE)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
