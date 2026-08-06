"""Idempotency mapping from one legacy identity to a formal target row."""

from __future__ import annotations

from datetime import datetime
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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LegacyMapping(Base):
    """Stable source-to-target identity used by later apply services."""

    __tablename__ = "legacy_mappings"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "import_staging_record_id",
                "import_run_id",
                "source_table",
                "source_row_number",
                "source_key",
            ],
            [
                "import_staging_records.id",
                "import_staging_records.import_run_id",
                "import_staging_records.source_table",
                "import_staging_records.source_row_number",
                "import_staging_records.source_key",
            ],
            name="fk_legacy_mappings_staging_trace_staging_records",
        ),
        ForeignKeyConstraint(
            ["import_run_id", "source_system"],
            ["import_runs.id", "import_runs.source_system"],
            name="fk_legacy_mappings_run_system_import_runs",
        ),
        UniqueConstraint(
            "source_system",
            "source_table",
            "source_key",
            "target_table",
            "mapping_slot",
            name="uq_legacy_mappings_source_identity_target_slot",
        ),
        CheckConstraint(
            "source_row_number > 0",
            name="ck_legacy_mappings_source_row_number_positive",
        ),
        CheckConstraint(
            "btrim(source_system) <> '' AND btrim(source_table) <> '' "
            "AND btrim(source_key) <> '' AND btrim(target_table) <> '' "
            "AND btrim(mapping_slot) <> ''",
            name="ck_legacy_mappings_stable_identity_nonblank",
        ),
        Index("ix_legacy_mappings_import_run_id", "import_run_id"),
        Index(
            "ix_legacy_mappings_target_table_target_id",
            "target_table",
            "target_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    import_run_id: Mapped[UUID] = mapped_column()
    import_staging_record_id: Mapped[UUID] = mapped_column()
    source_system: Mapped[str] = mapped_column(String(64))
    source_table: Mapped[str] = mapped_column(String(128))
    source_row_number: Mapped[int] = mapped_column(Integer)
    source_key: Mapped[str] = mapped_column(String(256))
    target_table: Mapped[str] = mapped_column(String(128))
    mapping_slot: Mapped[str] = mapped_column(
        String(64), default="primary", server_default="primary"
    )
    target_id: Mapped[UUID] = mapped_column()
    mapped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
