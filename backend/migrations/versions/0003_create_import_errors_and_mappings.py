"""Create import error tracking and legacy mapping tables.

Revision ID: 0003_import_trace
Revises: 0002_import_staging
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_import_trace"
down_revision: str | Sequence[str] | None = "0002_import_staging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create trace-consistent error and mapping structures."""

    op.create_table(
        "import_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("error_scope", sa.String(16), nullable=False),
        sa.Column("import_source_file_id", sa.Uuid(), nullable=True),
        sa.Column("import_staging_record_id", sa.Uuid(), nullable=True),
        sa.Column("source_table", sa.String(128), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_value", postgresql.JSONB(), nullable=True),
        sa.Column(
            "resolution_status",
            sa.String(16),
            server_default="open",
            nullable=False,
        ),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_row_number IS NULL OR source_row_number > 0",
            name="ck_import_errors_source_row_number_positive",
        ),
        sa.CheckConstraint(
            "error_scope IN ('run', 'file', 'row', 'field')",
            name="ck_import_errors_error_scope_allowed",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "resolution_status IN ('open', 'resolved', 'ignored')",
            name="ck_import_errors_resolution_status_allowed",
        ),
        sa.CheckConstraint(
            "(resolution_status = 'open' AND resolved_at IS NULL) OR "
            "(resolution_status IN ('resolved', 'ignored') "
            "AND resolved_at IS NOT NULL)",
            name="ck_import_errors_resolution_timestamp",
        ),
        sa.CheckConstraint(
            "resolution_status <> 'ignored' OR "
            "btrim(COALESCE(resolution_note, '')) <> ''",
            name="ck_import_errors_ignored_resolution_note",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_import_errors_import_run_id_import_runs",
        ),
        sa.ForeignKeyConstraint(
            ["import_source_file_id", "import_run_id", "source_table"],
            [
                "import_source_files.id",
                "import_source_files.import_run_id",
                "import_source_files.source_table",
            ],
            name="fk_import_errors_file_run_table_source_files",
        ),
        sa.ForeignKeyConstraint(
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_errors_import_run_id_resolution_status",
        "import_errors",
        ["import_run_id", "resolution_status"],
    )
    op.create_index(
        "ix_import_errors_run_table_source_row_number",
        "import_errors",
        ["import_run_id", "source_table", "source_row_number"],
    )

    op.create_table(
        "legacy_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("import_staging_record_id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.String(64), nullable=False),
        sa.Column("source_table", sa.String(128), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(256), nullable=False),
        sa.Column("target_table", sa.String(128), nullable=False),
        sa.Column(
            "mapping_slot", sa.String(64), server_default="primary", nullable=False
        ),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column(
            "mapped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_row_number > 0",
            name="ck_legacy_mappings_source_row_number_positive",
        ),
        sa.CheckConstraint(
            "btrim(source_system) <> '' AND btrim(source_table) <> '' "
            "AND btrim(source_key) <> '' AND btrim(target_table) <> '' "
            "AND btrim(mapping_slot) <> ''",
            name="ck_legacy_mappings_stable_identity_nonblank",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["import_run_id", "source_system"],
            ["import_runs.id", "import_runs.source_system"],
            name="fk_legacy_mappings_run_system_import_runs",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_system",
            "source_table",
            "source_key",
            "target_table",
            "mapping_slot",
            name="uq_legacy_mappings_source_identity_target_slot",
        ),
    )
    op.create_index(
        "ix_legacy_mappings_import_run_id",
        "legacy_mappings",
        ["import_run_id"],
    )
    op.create_index(
        "ix_legacy_mappings_target_table_target_id",
        "legacy_mappings",
        ["target_table", "target_id"],
    )


def downgrade() -> None:
    """Remove mapping and error structures in reverse order."""
    op.drop_table("legacy_mappings")
    op.drop_table("import_errors")
