"""Per-company document number sequence."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentSequence(Base):
    __tablename__ = "document_sequences"
    __table_args__ = (
        CheckConstraint("next_value >= 1", name="ck_document_sequences_next_value_positive"),
        Index(
            "uq_document_sequences_scope",
            "organization_id",
            "document_type",
            "period_key",
            unique=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "organizations.id", name="fk_document_sequences_organization", ondelete="RESTRICT"
        )
    )
    document_type: Mapped[str] = mapped_column(String(32))
    period_key: Mapped[str] = mapped_column(String(16))
    next_value: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
