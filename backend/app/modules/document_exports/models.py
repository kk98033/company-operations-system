"""Immutable generated PDF artifact."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentExport(Base):
    __tablename__ = "document_exports"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('quotation','work_order','shipment','statement')",
            name="ck_document_exports_type",
        ),
        CheckConstraint("content_type = 'application/pdf'", name="ck_document_exports_pdf"),
        CheckConstraint("byte_size > 0 AND octet_length(content) = byte_size", name="ck_document_exports_size"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_document_exports_sha256"),
        ForeignKeyConstraint(
            ["organization_id", "created_by_membership_id", "created_by_user_id"],
            [
                "organization_members.organization_id",
                "organization_members.id",
                "organization_members.user_id",
            ],
            name="fk_document_exports_creator_scope",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id",
            "document_type",
            "document_id",
            "document_version",
            "template_version",
            name="uq_document_exports_version",
        ),
        Index(
            "ix_document_exports_org_document",
            "organization_id",
            "document_type",
            "document_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    document_type: Mapped[str] = mapped_column(String(20))
    document_id: Mapped[UUID]
    document_number: Mapped[str] = mapped_column(String(128))
    document_version: Mapped[str] = mapped_column(String(64))
    template_version: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(32), default="application/pdf")
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_by_membership_id: Mapped[UUID]
    created_by_user_id: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
