"""Paper quality/type catalog."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaperType(Base):
    __tablename__ = "paper_types"
    __table_args__ = (
        CheckConstraint("btrim(code) <> ''", name="ck_paper_types_code_nonblank"),
        CheckConstraint("btrim(name) <> ''", name="ck_paper_types_name_nonblank"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_paper_types_status_allowed"),
        CheckConstraint("sort_order >= 0", name="ck_paper_types_sort_nonnegative"),
        Index(
            "uq_paper_types_org_code", "organization_id", text("lower(btrim(code))"), unique=True
        ),
        Index(
            "uq_paper_types_org_name", "organization_id", text("lower(btrim(name))"), unique=True
        ),
        Index("ix_paper_types_org_sort", "organization_id", "status", "sort_order", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", name="fk_paper_types_organization", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
