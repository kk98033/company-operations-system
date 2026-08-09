"""Organization tenant root."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Organization(Base):
    """One company boundary; profile details are added in Phase 2."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''", name="ck_organizations_name_nonblank"
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_organizations_status_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
