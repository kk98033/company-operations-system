"""Organization-owned customer master record."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("btrim(code) <> ''", name="ck_customers_code_nonblank"),
        CheckConstraint("btrim(name) <> ''", name="ck_customers_name_nonblank"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_customers_status_allowed"),
        CheckConstraint(
            "(legacy_source_table IS NULL) = (legacy_source_key IS NULL)",
            name="ck_customers_legacy_source_pair",
        ),
        UniqueConstraint("organization_id", "id", name="uq_customers_organization_id_id"),
        Index(
            "uq_customers_organization_normalized_code", "organization_id",
            text("lower(btrim(code))"), unique=True,
        ),
        Index(
            "ix_customers_organization_status_name", "organization_id", "status", "name", "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "organizations.id", name="fk_customers_organization_id_organizations",
            ondelete="RESTRICT",
        )
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str | None] = mapped_column(String(100))
    tax_identifier: Mapped[str | None] = mapped_column(String(20))
    contact_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    phone_secondary: Mapped[str | None] = mapped_column(String(32))
    mobile: Mapped[str | None] = mapped_column(String(32))
    fax: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(254))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    city: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(500))
    payment_terms: Mapped[str | None] = mapped_column(String(200))
    legacy_tax_setting_raw: Mapped[str | None] = mapped_column(String(16))
    legacy_rounding_setting_raw: Mapped[str | None] = mapped_column(String(16))
    legacy_source_table: Mapped[str | None] = mapped_column(String(64))
    legacy_source_key: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
