"""Mutable login throttle state containing no raw identity input."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoginThrottleState(Base):
    """One bounded failure counter for an organization/login fingerprint."""

    __tablename__ = "login_throttle_states"
    __table_args__ = (
        CheckConstraint(
            "credential_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_login_throttle_states_fingerprint_format",
        ),
        CheckConstraint(
            "failure_count >= 1",
            name="ck_login_throttle_states_failure_count_positive",
        ),
        CheckConstraint(
            "last_failed_at >= window_started_at",
            name="ck_login_throttle_states_failure_time_order",
        ),
        CheckConstraint(
            "blocked_until IS NULL OR blocked_until > last_failed_at",
            name="ck_login_throttle_states_blocked_after_failure",
        ),
    )

    credential_fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    failure_count: Mapped[int] = mapped_column(Integer)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
