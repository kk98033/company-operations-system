"""Immutable source-file manifest entry model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportSourceFile(Base):
    """File identity and counts retained without copying production rows into Git."""

    __tablename__ = "import_source_files"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "import_run_id",
            "source_table",
            name="uq_import_source_files_id_run_table",
        ),
        UniqueConstraint(
            "import_run_id",
            "source_relative_path",
            name="uq_import_source_files_import_run_id_source_relative_path",
        ),
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_import_source_files_content_sha256_format",
        ),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="ck_import_source_files_file_size_bytes_nonnegative",
        ),
        CheckConstraint(
            "physical_line_count IS NULL OR physical_line_count >= 0",
            name="ck_import_source_files_physical_line_count_nonnegative",
        ),
        CheckConstraint(
            "logical_row_count_including_header IS NULL OR "
            "logical_row_count_including_header >= 0",
            name="ck_import_source_files_logical_rows_nonnegative",
        ),
        CheckConstraint(
            "data_row_count IS NULL OR data_row_count >= 0",
            name="ck_import_source_files_data_row_count_nonnegative",
        ),
        Index(
            "ix_import_source_files_import_run_id_source_table",
            "import_run_id",
            "source_table",
        ),
        Index(
            "ix_import_source_files_source_table_content_sha256",
            "source_table",
            "content_sha256",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_runs.id", name="fk_import_source_files_import_run_id_import_runs")
    )
    source_relative_path: Mapped[str] = mapped_column(String(512))
    source_table: Mapped[str] = mapped_column(String(128))
    content_sha256: Mapped[str] = mapped_column(String(64))
    encoding_name: Mapped[str | None] = mapped_column(String(64))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    physical_line_count: Mapped[int | None] = mapped_column(Integer)
    logical_row_count_including_header: Mapped[int | None] = mapped_column(Integer)
    data_row_count: Mapped[int | None] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
