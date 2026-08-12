"""Supplier or production collaborator master record."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (
        CheckConstraint("btrim(code) <> ''", name="ck_vendors_code_nonblank"),
        CheckConstraint("btrim(name) <> ''", name="ck_vendors_name_nonblank"),
        CheckConstraint(
            "category IN ('supplier', 'collaborator')",
            name="ck_vendors_category_allowed",
        ),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_vendors_status_allowed"),
        CheckConstraint(
            "settlement_day IS NULL OR settlement_day BETWEEN 1 AND 31",
            name="ck_vendors_settlement_day_range",
        ),
        Index(
            "uq_vendors_organization_normalized_code",
            "organization_id",
            text("lower(btrim(code))"),
            unique=True,
        ),
        Index("ix_vendors_organization_status_name", "organization_id", "status", "name", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", name="fk_vendors_organization", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20))
    contact_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    phone_secondary: Mapped[str | None] = mapped_column(String(32))
    mobile: Mapped[str | None] = mapped_column(String(32))
    fax: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(254))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    city: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(500))
    settlement_day: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
