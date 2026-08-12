"""Confirmed fixed production process definition."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessDefinition(Base):
    __tablename__ = "process_definitions"
    __table_args__ = (
        CheckConstraint("btrim(code) <> ''", name="ck_process_definitions_code_nonblank"),
        CheckConstraint("btrim(name) <> ''", name="ck_process_definitions_name_nonblank"),
        CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_process_definitions_status_allowed"
        ),
        CheckConstraint("sort_order BETWEEN 1 AND 13", name="ck_process_definitions_sort_range"),
        Index("uq_process_definitions_org_code", "organization_id", "code", unique=True),
        Index("uq_process_definitions_org_sort", "organization_id", "sort_order", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "organizations.id", name="fk_process_definitions_organization", ondelete="RESTRICT"
        )
    )
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
