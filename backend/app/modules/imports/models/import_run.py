"""Import-run audit model; it does not apply rows to business tables."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportRun(Base):
    """One independently auditable attempt against an immutable source snapshot."""

    __tablename__ = "import_runs"
    __table_args__ = (
        CheckConstraint(
            "source_manifest_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_import_runs_source_manifest_sha256_format",
        ),
        CheckConstraint(
            "status IN ('created', 'manifested', 'staged', 'validated', "
            "'awaiting_approval', 'applying', 'applied', 'reconciled', "
            "'accepted', 'failed', 'reconciliation_failed')",
            name="ck_import_runs_status_allowed",
        ),
        CheckConstraint(
            "source_data_row_count >= 0 AND staged_row_count >= 0 "
            "AND error_count >= 0 AND mapped_row_count >= 0",
            name="ck_import_runs_counts_nonnegative",
        ),
        UniqueConstraint(
            "id", "source_system", name="uq_import_runs_id_source_system"
        ),
        Index(
            "ix_import_runs_source_system_source_manifest_sha256",
            "source_system",
            "source_manifest_sha256",
        ),
        Index("ix_import_runs_status_created_at", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_system: Mapped[str] = mapped_column(String(64))
    source_manifest_sha256: Mapped[str] = mapped_column(String(64))
    importer_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(32), default="created", server_default="created"
    )
    source_data_row_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    staged_row_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    mapped_row_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
