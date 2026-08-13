"""Synthetic-only import rows shared by PostgreSQL acceptance tests."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Connection

from app.modules.imports.models import ImportRun, ImportSourceFile, ImportStagingRecord


def insert_import_run(
    connection: Connection,
    run_id: UUID,
    *,
    source_system: str = "synthetic_legacy",
    manifest_sha256: str = "a" * 64,
) -> None:
    connection.execute(
        ImportRun.__table__.insert(),
        {
            "id": run_id,
            "source_system": source_system,
            "source_manifest_sha256": manifest_sha256,
            "importer_version": "test-only-v1",
        },
    )


def insert_source_file(
    connection: Connection,
    *,
    run_id: UUID,
    source_file_id: UUID,
    source_table: str = "legacy_records",
) -> None:
    connection.execute(
        ImportSourceFile.__table__.insert(),
        {
            "id": source_file_id,
            "import_run_id": run_id,
            "source_relative_path": "tables/synthetic_records.csv",
            "source_table": source_table,
            "content_sha256": "b" * 64,
            "encoding_name": "utf-8",
            "file_size_bytes": 128,
            "physical_line_count": 2,
            "logical_row_count_including_header": 2,
            "data_row_count": 1,
        },
    )


def insert_staging_record(
    connection: Connection,
    *,
    run_id: UUID,
    source_file_id: UUID,
    staging_record_id: UUID,
    source_table: str = "legacy_records",
    source_row_number: int = 2,
    source_key: str | None = "synthetic-key-001",
) -> None:
    connection.execute(
        ImportStagingRecord.__table__.insert(),
        {
            "id": staging_record_id,
            "import_run_id": run_id,
            "import_source_file_id": source_file_id,
            "source_table": source_table,
            "source_row_number": source_row_number,
            "source_key": source_key,
            "raw_payload": {"legacy_label": "raw canary"},
            "normalized_payload": {"display_label": "normalized canary"},
            "validation_status": "valid",
        },
    )


def insert_staged_source(
    connection: Connection,
    *,
    run_id: UUID,
    source_file_id: UUID,
    staging_record_id: UUID,
) -> None:
    insert_source_file(connection, run_id=run_id, source_file_id=source_file_id)
    insert_staging_record(
        connection,
        run_id=run_id,
        source_file_id=source_file_id,
        staging_record_id=staging_record_id,
    )
