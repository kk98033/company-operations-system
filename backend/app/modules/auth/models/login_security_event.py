"""Append-only security event emitted by browser login attempts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoginSecurityEvent(Base):
    """Privacy-preserving evidence for login failures and recovery."""

    __tablename__ = "login_security_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('login_failed', 'login_rate_limited', 'login_succeeded', "
            "'session_replaced')",
            name="ck_login_security_events_type_allowed",
        ),
        CheckConstraint(
            "credential_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_login_security_events_fingerprint_format",
        ),
        CheckConstraint(
            "failure_count IS NULL OR failure_count >= 0",
            name="ck_login_security_events_failure_count_nonnegative",
        ),
        Index(
            "ix_login_security_events_fingerprint_created_at",
            "credential_fingerprint",
            "created_at",
        ),
        Index("ix_login_security_events_request_id", "request_id"),
        Index("ix_login_security_events_created_at", "created_at"),
        Index("ix_login_security_events_session_id", "session_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(32))
    credential_fingerprint: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[UUID] = mapped_column()
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "sessions.id",
            name="fk_login_security_events_session_id_sessions",
            ondelete="RESTRICT",
        )
    )
    failure_count: Mapped[int | None] = mapped_column(Integer)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
