"""Quotation detail row."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    __table_args__ = (
        CheckConstraint("line_number >= 1", name="ck_quotation_items_line_positive"),
        CheckConstraint("btrim(product_name) <> ''", name="ck_quotation_items_product_nonblank"),
        CheckConstraint("quantity > 0", name="ck_quotation_items_quantity_positive"),
        CheckConstraint(
            "unit_price >= 0 AND plate_fee >= 0 AND die_fee >= 0",
            name="ck_quotation_items_money_nonnegative",
        ),
        ForeignKeyConstraint(
            ["organization_id", "quotation_id"],
            ["quotations.organization_id", "quotations.id"],
            name="fk_quotation_items_quotation_scope",
            ondelete="CASCADE",
        ),
        UniqueConstraint("quotation_id", "line_number", name="uq_quotation_items_line"),
        Index(
            "ix_quotation_items_organization_quotation",
            "organization_id",
            "quotation_id",
            "line_number",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    quotation_id: Mapped[UUID]
    line_number: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(200))
    size: Mapped[str | None] = mapped_column(String(200))
    paper: Mapped[str | None] = mapped_column(String(200))
    color: Mapped[str | None] = mapped_column(String(100))
    coating: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    plate_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    die_fee: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
