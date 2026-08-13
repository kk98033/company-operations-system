"""Organization-scoped production case grouping one or more work orders."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductionCase(Base):
    __tablename__ = "production_cases"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'void')", name="ck_production_cases_status"),
        CheckConstraint("btrim(case_number) <> ''", name="ck_production_cases_number_nonblank"),
        CheckConstraint(
            "(status = 'void' AND voided_at IS NOT NULL AND btrim(void_reason) <> '') "
            "OR (status <> 'void' AND voided_at IS NULL AND void_reason IS NULL)",
            name="ck_production_cases_void_state",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_production_cases_customer_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_production_cases_quotation_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "id", name="uq_production_cases_org_id"),
        Index("uq_production_cases_org_number", "organization_id", "case_number", unique=True),
        Index(
            "uq_production_cases_org_source_quote",
            "organization_id",
            "source_quotation_id",
            unique=True,
            postgresql_where=text("source_quotation_id IS NOT NULL"),
        ),
        Index(
            "ix_production_cases_org_date_status", "organization_id", "case_date", "status", "id"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", name="fk_production_cases_org", ondelete="RESTRICT")
    )
    case_number: Mapped[str] = mapped_column(String(32))
    case_date: Mapped[date] = mapped_column(Date)
    customer_id: Mapped[UUID]
    organization_snapshot: Mapped[dict] = mapped_column(JSON)
    customer_snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    notes: Mapped[str | None] = mapped_column(Text)
    source_quotation_id: Mapped[UUID | None]
    legacy_document_number: Mapped[str | None] = mapped_column(String(128))
    legacy_source_table: Mapped[str | None] = mapped_column(String(64))
    legacy_source_key: Mapped[str | None] = mapped_column(String(128))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
