"""Server-side session model storing only a one-way token digest."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Session(Base):
    """One revocable login session bound to an organization membership."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "token_digest ~ '^[0-9a-f]{64}$'",
            name="ck_sessions_token_digest_format",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_sessions_expires_after_created",
        ),
        CheckConstraint(
            "last_seen_at IS NULL OR last_seen_at >= created_at",
            name="ck_sessions_last_seen_not_before_created",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_sessions_revoked_not_before_created",
        ),
        UniqueConstraint("token_digest", name="uq_sessions_token_digest"),
        Index(
            "ix_sessions_organization_member_id_expires_at",
            "organization_member_id",
            "expires_at",
        ),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_member_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "organization_members.id",
            name="fk_sessions_organization_member_id_organization_members",
            ondelete="RESTRICT",
        )
    )
    token_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
