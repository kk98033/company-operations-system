"""Append-only organization audit event."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Immutable audit event written in the business transaction."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "action = lower(btrim(action)) AND "
            "action ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_audit_logs_action_format",
        ),
        CheckConstraint(
            "entity_type = lower(btrim(entity_type)) AND "
            "entity_type ~ '^[a-z][a-z0-9_]*$'",
            name="ck_audit_logs_entity_type_format",
        ),
        CheckConstraint(
            "event_status IN ('success', 'failure')",
            name="ck_audit_logs_event_status_allowed",
        ),
        CheckConstraint(
            "actor_kind IN ('user', 'system')",
            name="ck_audit_logs_actor_kind_allowed",
        ),
        CheckConstraint(
            "(actor_kind = 'user' AND actor_membership_id IS NOT NULL "
            "AND actor_user_id IS NOT NULL) OR "
            "(actor_kind = 'system' AND actor_membership_id IS NULL "
            "AND actor_user_id IS NULL)",
            name="ck_audit_logs_actor_identity_consistent",
        ),
        CheckConstraint(
            "reason IS NULL OR btrim(reason) <> ''",
            name="ck_audit_logs_reason_nonblank",
        ),
        CheckConstraint(
            "document_number IS NULL OR btrim(document_number) <> ''",
            name="ck_audit_logs_document_number_nonblank",
        ),
        CheckConstraint(
            "before_data IS NULL OR jsonb_typeof(before_data) = 'object'",
            name="ck_audit_logs_before_data_object",
        ),
        CheckConstraint(
            "after_data IS NULL OR jsonb_typeof(after_data) = 'object'",
            name="ck_audit_logs_after_data_object",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_audit_logs_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_membership_id", "actor_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_audit_logs_actor_organization_members",
            ondelete="RESTRICT",
        ),
        Index("ix_audit_logs_organization_id_created_at", "organization_id", "created_at"),
        Index(
            "ix_audit_logs_organization_id_entity_type_entity_id",
            "organization_id",
            "entity_type",
            "entity_id",
        ),
        Index("ix_audit_logs_request_id", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column()
    actor_kind: Mapped[str] = mapped_column(String(16))
    actor_membership_id: Mapped[UUID | None] = mapped_column()
    actor_user_id: Mapped[UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID | None] = mapped_column()
    document_number: Mapped[str | None] = mapped_column(String(128))
    event_status: Mapped[str] = mapped_column(
        String(16), default="success", server_default="success"
    )
    reason: Mapped[str | None] = mapped_column(Text)
    before_data: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(none_as_null=True)
    )
    after_data: Mapped[dict[str, object] | None] = mapped_column(
        JSONB(none_as_null=True)
    )
    request_id: Mapped[UUID] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
