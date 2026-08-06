"""Structured import validation and resolution error model."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportError(Base):
    """A field, row, file, or run error with an explicit resolution state."""

    __tablename__ = "import_errors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["import_source_file_id", "import_run_id", "source_table"],
            [
                "import_source_files.id",
                "import_source_files.import_run_id",
                "import_source_files.source_table",
            ],
            name="fk_import_errors_file_run_table_source_files",
        ),
        ForeignKeyConstraint(
            [
                "import_staging_record_id",
                "import_run_id",
                "import_source_file_id",
                "source_table",
                "source_row_number",
            ],
            [
                "import_staging_records.id",
                "import_staging_records.import_run_id",
                "import_staging_records.import_source_file_id",
                "import_staging_records.source_table",
                "import_staging_records.source_row_number",
            ],
            name="fk_import_errors_staging_trace_staging_records",
        ),
        CheckConstraint(
            "source_row_number IS NULL OR source_row_number > 0",
            name="ck_import_errors_source_row_number_positive",
        ),
        CheckConstraint(
            "error_scope IN ('run', 'file', 'row', 'field')",
            name="ck_import_errors_error_scope_allowed",
        ),
        CheckConstraint(
            "(error_scope = 'run' AND import_source_file_id IS NULL "
            "AND import_staging_record_id IS NULL AND source_table IS NULL "
            "AND source_row_number IS NULL AND field_name IS NULL) OR "
            "(error_scope = 'file' AND import_source_file_id IS NOT NULL "
            "AND import_staging_record_id IS NULL AND source_table IS NOT NULL "
            "AND source_row_number IS NULL AND field_name IS NULL) OR "
            "(error_scope = 'row' AND import_source_file_id IS NOT NULL "
            "AND import_staging_record_id IS NOT NULL AND source_table IS NOT NULL "
            "AND source_row_number IS NOT NULL AND field_name IS NULL) OR "
            "(error_scope = 'field' AND import_source_file_id IS NOT NULL "
            "AND import_staging_record_id IS NOT NULL AND source_table IS NOT NULL "
            "AND source_row_number IS NOT NULL AND field_name IS NOT NULL)",
            name="ck_import_errors_scope_trace_shape",
        ),
        CheckConstraint(
            "resolution_status IN ('open', 'resolved', 'ignored')",
            name="ck_import_errors_resolution_status_allowed",
        ),
        CheckConstraint(
            "(resolution_status = 'open' AND resolved_at IS NULL) OR "
            "(resolution_status IN ('resolved', 'ignored') "
            "AND resolved_at IS NOT NULL)",
            name="ck_import_errors_resolution_timestamp",
        ),
        CheckConstraint(
            "resolution_status <> 'ignored' OR "
            "btrim(COALESCE(resolution_note, '')) <> ''",
            name="ck_import_errors_ignored_resolution_note",
        ),
        Index(
            "ix_import_errors_import_run_id_resolution_status",
            "import_run_id",
            "resolution_status",
        ),
        Index(
            "ix_import_errors_run_table_source_row_number",
            "import_run_id",
            "source_table",
            "source_row_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_runs.id", name="fk_import_errors_import_run_id_import_runs")
    )
    error_scope: Mapped[str] = mapped_column(String(16))
    import_source_file_id: Mapped[UUID | None] = mapped_column()
    import_staging_record_id: Mapped[UUID | None] = mapped_column()
    source_table: Mapped[str | None] = mapped_column(String(128))
    source_row_number: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(128))
    error_code: Mapped[str] = mapped_column(String(64))
    error_message: Mapped[str] = mapped_column(Text)
    raw_value: Mapped[Any | None] = mapped_column(JSONB)
    resolution_status: Mapped[str] = mapped_column(
        String(16), default="open", server_default="open"
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
