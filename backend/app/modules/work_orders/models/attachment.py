"""Private work-order attachment stored behind authenticated API access."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkOrderAttachment(Base):
    __tablename__ = "work_order_attachments"
    __table_args__ = (
        CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 5242880", name="ck_work_order_attachments_size"
        ),
        CheckConstraint(
            "octet_length(content) = size_bytes", name="ck_work_order_attachments_content_size"
        ),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_work_order_attachments_sha256"),
        ForeignKeyConstraint(
            ["organization_id", "work_order_id"],
            ["work_orders.organization_id", "work_orders.id"],
            name="fk_work_order_attachments_order_scope",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_work_order_attachments_org_order", "organization_id", "work_order_id", "created_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID]
    work_order_id: Mapped[UUID]
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
