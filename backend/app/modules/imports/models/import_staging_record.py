"""Raw and normalized staging payload model."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportStagingRecord(Base):
    """One source row staged before any domain mapping or formal write."""

    __tablename__ = "import_staging_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["import_source_file_id", "import_run_id", "source_table"],
            [
                "import_source_files.id",
                "import_source_files.import_run_id",
                "import_source_files.source_table",
            ],
            name="fk_import_staging_records_file_run_table_source_files",
        ),
        UniqueConstraint(
            "id",
            "import_run_id",
            "import_source_file_id",
            "source_table",
            "source_row_number",
            name="uq_import_staging_records_identity_with_file",
        ),
        UniqueConstraint(
            "id",
            "import_run_id",
            "source_table",
            "source_row_number",
            "source_key",
            name="uq_import_staging_records_identity_with_key",
        ),
        UniqueConstraint(
            "import_source_file_id",
            "source_row_number",
            name="uq_import_staging_records_source_file_id_row_number",
        ),
        CheckConstraint(
            "source_row_number > 0",
            name="ck_import_staging_records_source_row_number_positive",
        ),
        CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid')",
            name="ck_import_staging_records_validation_status_allowed",
        ),
        Index(
            "ix_import_staging_records_import_run_id_validation_status",
            "import_run_id",
            "validation_status",
        ),
        Index(
            "ix_import_staging_records_run_table_source_key",
            "import_run_id",
            "source_table",
            "source_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column()
    import_source_file_id: Mapped[UUID] = mapped_column()
    source_table: Mapped[str] = mapped_column(String(128))
    source_row_number: Mapped[int] = mapped_column(Integer)
    source_key: Mapped[str | None] = mapped_column(String(256))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    normalized_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validation_status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending"
    )
    staged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
