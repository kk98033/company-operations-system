"""Company-scoped defaults and signed-off policy versions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrganizationSettings(Base):
    """One settings row whose ownership is exactly one organization."""

    __tablename__ = "organization_settings"
    __table_args__ = (
        CheckConstraint(
            "statement_rounding_scope IS NULL OR "
            "statement_rounding_scope IN ('per_line', 'grand_total')",
            name="ck_organization_settings_rounding_scope_allowed",
        ),
        CheckConstraint(
            "statement_rounding_decimal_places IS NULL OR "
            "statement_rounding_decimal_places BETWEEN 0 AND 4",
            name="ck_organization_settings_rounding_places_range",
        ),
        CheckConstraint(
            "(statement_tax_default_enabled = false "
            "AND statement_tax_rate_percent IS NULL "
            "AND statement_rounding_scope IS NULL "
            "AND statement_rounding_decimal_places IS NULL) OR "
            "(statement_tax_default_enabled = true "
            "AND statement_tax_rate_percent > 0 "
            "AND statement_tax_rate_percent <= 100 "
            "AND statement_rounding_scope IS NOT NULL "
            "AND statement_rounding_decimal_places IS NOT NULL)",
            name="ck_organization_settings_statement_tax_complete",
        ),
        CheckConstraint(
            "document_number_policy_version = 'adr-018-v1'",
            name="ck_organization_settings_number_policy_v1",
        ),
        CheckConstraint(
            "quotation_print_layout_version = 'gmail-a4-landscape-v1'",
            name="ck_organization_settings_quotation_print_v1",
        ),
        CheckConstraint(
            "work_order_print_layout_version = 'gmail-a4-portrait-9-process-v1'",
            name="ck_organization_settings_work_order_print_v1",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "organizations.id",
            name="fk_organization_settings_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )
    statement_tax_default_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    statement_tax_rate_percent: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    statement_rounding_scope: Mapped[str | None] = mapped_column(String(16))
    statement_rounding_decimal_places: Mapped[int | None] = mapped_column(SmallInteger)
    document_number_policy_version: Mapped[str] = mapped_column(
        String(32), default="adr-018-v1", server_default="adr-018-v1"
    )
    quotation_print_layout_version: Mapped[str] = mapped_column(
        String(64),
        default="gmail-a4-landscape-v1",
        server_default="gmail-a4-landscape-v1",
    )
    work_order_print_layout_version: Mapped[str] = mapped_column(
        String(64),
        default="gmail-a4-portrait-9-process-v1",
        server_default="gmail-a4-portrait-9-process-v1",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
