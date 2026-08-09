"""Same-organization membership-to-role assignment."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKeyConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrganizationMemberRole(Base):
    """Assign a role while composite FKs forbid cross-organization leakage."""

    __tablename__ = "organization_member_roles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "organization_member_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
            ],
            name=(
                "fk_organization_member_roles_member_"
                "organization_members"
            ),
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "role_id"],
            ["roles.organization_id", "roles.id"],
            name="fk_organization_member_roles_role_roles",
            ondelete="RESTRICT",
        ),
        Index("ix_organization_member_roles_role_id", "role_id"),
        Index(
            "ix_organization_member_roles_organization_id",
            "organization_id",
        ),
    )

    organization_member_id: Mapped[UUID] = mapped_column(primary_key=True)
    role_id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
