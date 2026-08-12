"""Organization tenant root."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Organization(Base):
    """One company boundary and its printable company profile."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''", name="ck_organizations_name_nonblank"
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_organizations_status_allowed",
        ),
        CheckConstraint(
            "tax_identifier IS NULL OR btrim(tax_identifier) <> ''",
            name="ck_organizations_tax_identifier_nonblank",
        ),
        CheckConstraint(
            "representative_name IS NULL OR btrim(representative_name) <> ''",
            name="ck_organizations_representative_name_nonblank",
        ),
        CheckConstraint(
            "phone IS NULL OR btrim(phone) <> ''",
            name="ck_organizations_phone_nonblank",
        ),
        CheckConstraint(
            "fax IS NULL OR btrim(fax) <> ''",
            name="ck_organizations_fax_nonblank",
        ),
        CheckConstraint(
            "email IS NULL OR btrim(email) <> ''",
            name="ck_organizations_email_nonblank",
        ),
        CheckConstraint(
            "address IS NULL OR btrim(address) <> ''",
            name="ck_organizations_address_nonblank",
        ),
        CheckConstraint(
            "logo_sha256 IS NULL OR logo_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_organizations_logo_sha256_format",
        ),
        CheckConstraint(
            "(logo_object_key IS NULL AND logo_content_type IS NULL "
            "AND logo_original_filename IS NULL AND logo_sha256 IS NULL) OR "
            "(logo_object_key IS NOT NULL AND logo_content_type IS NOT NULL "
            "AND logo_original_filename IS NOT NULL AND logo_sha256 IS NOT NULL)",
            name="ck_organizations_logo_metadata_complete",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    tax_identifier: Mapped[str | None] = mapped_column(String(20))
    representative_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    fax: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(254))
    address: Mapped[str | None] = mapped_column(String(500))
    logo_object_key: Mapped[str | None] = mapped_column(String(512))
    logo_content_type: Mapped[str | None] = mapped_column(String(100))
    logo_original_filename: Mapped[str | None] = mapped_column(String(255))
    logo_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
