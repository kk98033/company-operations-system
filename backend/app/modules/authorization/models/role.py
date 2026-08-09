"""Organization-owned role definition."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(Base):
    """A named permission collection that belongs to one organization."""

    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "code = lower(btrim(code)) AND code ~ '^[a-z][a-z0-9_]*$'",
            name="ck_roles_code_format",
        ),
        CheckConstraint("btrim(name) <> ''", name="ck_roles_name_nonblank"),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_roles_status_allowed",
        ),
        UniqueConstraint(
            "organization_id", "code", name="uq_roles_organization_id_code"
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_roles_organization_id_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "organizations.id",
            name="fk_roles_organization_id_organizations",
            ondelete="RESTRICT",
        )
    )
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
