"""Append-only security event emitted by browser login attempts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SecurityEvent(Base):
    """Privacy-preserving evidence for authentication and authorization events.

    The physical table name is retained for migration compatibility with the
    original login-only event store.
    """

    __tablename__ = "login_security_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('login_failed', 'login_rate_limited', 'login_succeeded', "
            "'session_replaced', 'logout_succeeded', 'session_revoked', "
            "'membership_sessions_revoked', 'permission_denied')",
            name="ck_login_security_events_type_allowed",
        ),
        CheckConstraint(
            "credential_fingerprint IS NULL OR "
            "credential_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_login_security_events_fingerprint_format",
        ),
        CheckConstraint(
            "(event_type IN ('login_failed', 'login_rate_limited', "
            "'login_succeeded', 'session_replaced') AND "
            "credential_fingerprint IS NOT NULL) OR "
            "(event_type IN ('logout_succeeded', 'session_revoked', "
            "'membership_sessions_revoked', 'permission_denied') AND "
            "credential_fingerprint IS NULL AND organization_id IS NOT NULL AND "
            "actor_membership_id IS NOT NULL AND actor_user_id IS NOT NULL AND "
            "session_id IS NOT NULL)",
            name="ck_login_security_events_identity_consistent",
        ),
        CheckConstraint(
            "(target_type IS NULL AND target_id IS NULL) OR "
            "(target_type IS NOT NULL AND target_id IS NOT NULL)",
            name="ck_login_security_events_target_consistent",
        ),
        CheckConstraint(
            "target_type IS NULL OR (target_type = lower(btrim(target_type)) AND "
            "target_type ~ '^[a-z][a-z0-9_]*$')",
            name="ck_login_security_events_target_type_format",
        ),
        CheckConstraint(
            "capability IS NULL OR (capability = lower(btrim(capability)) AND "
            "capability ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$')",
            name="ck_login_security_events_capability_format",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_login_security_events_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_login_security_events_actor_organization_members",
            ondelete="RESTRICT",
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
        Index(
            "ix_login_security_events_organization_id_created_at",
            "organization_id",
            "created_at",
        ),
        Index(
            "ix_login_security_events_actor_membership_id_created_at",
            "actor_membership_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(32))
    credential_fingerprint: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[UUID] = mapped_column()
    organization_id: Mapped[UUID | None] = mapped_column()
    actor_membership_id: Mapped[UUID | None] = mapped_column()
    actor_user_id: Mapped[UUID | None] = mapped_column()
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "sessions.id",
            name="fk_login_security_events_session_id_sessions",
            ondelete="RESTRICT",
        )
    )
    failure_count: Mapped[int | None] = mapped_column(Integer)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[UUID | None] = mapped_column()
    capability: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Backward-compatible import for the login throttle service and older tests.
LoginSecurityEvent = SecurityEvent
