"""Create import run, source-file, and staging tables.

Revision ID: 0002_import_staging
Revises: 0001_empty_baseline
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_import_staging"
down_revision: str | Sequence[str] | None = "0001_empty_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create source audit and staging structures only."""

    op.create_table(
        "import_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.String(64), nullable=False),
        sa.Column("source_manifest_sha256", sa.String(64), nullable=False),
        sa.Column("importer_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), server_default="created", nullable=False),
        sa.Column(
            "source_data_row_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("staged_row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("mapped_row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_manifest_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_import_runs_source_manifest_sha256_format",
        ),
        sa.CheckConstraint(
            "status IN ('created', 'manifested', 'staged', 'validated', "
            "'awaiting_approval', 'applying', 'applied', 'reconciled', "
            "'accepted', 'failed', 'reconciliation_failed')",
            name="ck_import_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "source_data_row_count >= 0 AND staged_row_count >= 0 "
            "AND error_count >= 0 AND mapped_row_count >= 0",
            name="ck_import_runs_counts_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "source_system", name="uq_import_runs_id_source_system"
        ),
    )
    op.create_index(
        "ix_import_runs_source_system_source_manifest_sha256",
        "import_runs",
        ["source_system", "source_manifest_sha256"],
    )
    op.create_index(
        "ix_import_runs_status_created_at", "import_runs", ["status", "created_at"]
    )

    op.create_table(
        "import_source_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_relative_path", sa.String(512), nullable=False),
        sa.Column("source_table", sa.String(128), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("encoding_name", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("physical_line_count", sa.Integer(), nullable=True),
        sa.Column("logical_row_count_including_header", sa.Integer(), nullable=True),
        sa.Column("data_row_count", sa.Integer(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_import_source_files_content_sha256_format",
        ),
        sa.CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="ck_import_source_files_file_size_bytes_nonnegative",
        ),
        sa.CheckConstraint(
            "physical_line_count IS NULL OR physical_line_count >= 0",
            name="ck_import_source_files_physical_line_count_nonnegative",
        ),
        sa.CheckConstraint(
            "logical_row_count_including_header IS NULL OR "
            "logical_row_count_including_header >= 0",
            name="ck_import_source_files_logical_rows_nonnegative",
        ),
        sa.CheckConstraint(
            "data_row_count IS NULL OR data_row_count >= 0",
            name="ck_import_source_files_data_row_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_import_source_files_import_run_id_import_runs",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "import_run_id",
            "source_table",
            name="uq_import_source_files_id_run_table",
        ),
        sa.UniqueConstraint(
            "import_run_id",
            "source_relative_path",
            name="uq_import_source_files_import_run_id_source_relative_path",
        ),
    )
    op.create_index(
        "ix_import_source_files_import_run_id_source_table",
        "import_source_files",
        ["import_run_id", "source_table"],
    )
    op.create_index(
        "ix_import_source_files_source_table_content_sha256",
        "import_source_files",
        ["source_table", "content_sha256"],
    )

    op.create_table(
        "import_staging_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_run_id", sa.Uuid(), nullable=False),
        sa.Column("import_source_file_id", sa.Uuid(), nullable=False),
        sa.Column("source_table", sa.String(128), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(256), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "validation_status",
            sa.String(16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "staged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_row_number > 0",
            name="ck_import_staging_records_source_row_number_positive",
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid')",
            name="ck_import_staging_records_validation_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["import_source_file_id", "import_run_id", "source_table"],
            [
                "import_source_files.id",
                "import_source_files.import_run_id",
                "import_source_files.source_table",
            ],
            name="fk_import_staging_records_file_run_table_source_files",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "import_run_id",
            "import_source_file_id",
            "source_table",
            "source_row_number",
            name="uq_import_staging_records_identity_with_file",
        ),
        sa.UniqueConstraint(
            "id",
            "import_run_id",
            "source_table",
            "source_row_number",
            "source_key",
            name="uq_import_staging_records_identity_with_key",
        ),
        sa.UniqueConstraint(
            "import_source_file_id",
            "source_row_number",
            name="uq_import_staging_records_source_file_id_row_number",
        ),
    )
    op.create_index(
        "ix_import_staging_records_import_run_id_validation_status",
        "import_staging_records",
        ["import_run_id", "validation_status"],
    )
    op.create_index(
        "ix_import_staging_records_run_table_source_key",
        "import_staging_records",
        ["import_run_id", "source_table", "source_key"],
    )


def downgrade() -> None:
    """Remove staging structures in reverse dependency order."""
    op.drop_table("import_staging_records")
    op.drop_table("import_source_files")
    op.drop_table("import_runs")
