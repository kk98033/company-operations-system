"""Metadata contract for the audit-only import foundation."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportSourceFile,
    ImportStagingRecord,
    LegacyMapping,
)


def _unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    tables = {
        ImportRun.__tablename__: ImportRun.__table__,
        ImportSourceFile.__tablename__: ImportSourceFile.__table__,
        ImportStagingRecord.__tablename__: ImportStagingRecord.__table__,
        LegacyMapping.__tablename__: LegacyMapping.__table__,
    }
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in tables[table_name].constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _check_sql(model: type[object]) -> str:
    return " ".join(
        str(constraint.sqltext)
        for constraint in model.__table__.constraints  # type: ignore[attr-defined]
        if isinstance(constraint, CheckConstraint)
    )


def test_import_run_allows_same_manifest_to_be_retried() -> None:
    unique_columns = _unique_column_sets("import_runs")

    assert ("source_system", "source_manifest_sha256") not in unique_columns
    assert "created" in _check_sql(ImportRun)
    assert "awaiting_approval" in _check_sql(ImportRun)
    assert "reconciliation_failed" in _check_sql(ImportRun)


def test_staging_preserves_traceable_raw_and_normalized_payloads() -> None:
    columns = ImportStagingRecord.__table__.c

    assert isinstance(columns.raw_payload.type, JSONB)
    assert isinstance(columns.normalized_payload.type, JSONB)
    assert columns.raw_payload.nullable is False
    assert columns.normalized_payload.nullable is True
    assert columns.source_key.nullable is True
    assert columns.source_key.type.length == 256
    assert ("import_source_file_id", "source_row_number") in _unique_column_sets(
        "import_staging_records"
    )


def test_error_supports_file_row_and_field_scopes() -> None:
    columns = ImportError.__table__.c

    assert columns.error_scope.nullable is False
    assert columns.import_source_file_id.nullable is True
    assert columns.import_staging_record_id.nullable is True
    assert columns.source_row_number.nullable is True
    assert columns.field_name.nullable is True
    assert isinstance(columns.raw_value.type, JSONB)
    assert "error_scope = 'file'" in _check_sql(ImportError)
    assert "error_scope = 'field'" in _check_sql(ImportError)


def test_mapping_idempotency_crosses_runs_and_supports_child_slots() -> None:
    assert (
        "source_system",
        "source_table",
        "source_key",
        "target_table",
        "mapping_slot",
    ) in _unique_column_sets("legacy_mappings")
    assert all("import_run_id" not in columns for columns in _unique_column_sets("legacy_mappings"))
    assert LegacyMapping.__table__.c.source_key.type.length == 256
    assert LegacyMapping.__table__.c.mapping_slot.type.length == 64


def test_source_file_counts_keep_physical_logical_and_data_meanings_separate() -> None:
    columns = ImportSourceFile.__table__.c

    assert columns.file_size_bytes.nullable is True
    assert columns.physical_line_count.nullable is True
    assert columns.logical_row_count_including_header.nullable is True
    assert columns.data_row_count.nullable is True
    assert "source_data_row_count" in ImportRun.__table__.c
