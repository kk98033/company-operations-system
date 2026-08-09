"""Global user identity; organization access is defined by memberships."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """One independently authenticated employee identity."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "btrim(login_name) <> '' AND btrim(display_name) <> '' "
            "AND btrim(password_hash) <> ''",
            name="ck_users_required_text_nonblank",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'locked')",
            name="ck_users_status_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    login_name: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(
        String(16), default="active", server_default="active"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


Index(
    "uq_users_login_name_normalized",
    func.lower(func.btrim(User.login_name)),
    unique=True,
)
