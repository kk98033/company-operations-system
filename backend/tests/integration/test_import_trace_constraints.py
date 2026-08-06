"""Negative PostgreSQL checks for denormalized import trace integrity."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Connection, Engine, Table
from sqlalchemy.exc import IntegrityError

from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportSourceFile,
    LegacyMapping,
)
from tests.integration.synthetic_import_data import (
    insert_import_run,
    insert_source_file,
    insert_staged_source,
    insert_staging_record,
)

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def _seed_trace(connection: Connection) -> tuple[UUID, UUID, UUID]:
    run_id = uuid4()
    source_file_id = uuid4()
    staging_record_id = uuid4()
    insert_import_run(connection, run_id)
    insert_staged_source(
        connection,
        run_id=run_id,
        source_file_id=source_file_id,
        staging_record_id=staging_record_id,
    )
    return run_id, source_file_id, staging_record_id


def _assert_insert_rejected(
    connection: Connection, table: Table, values: dict[str, object]
) -> None:
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            connection.execute(table.insert(), values)


def test_staging_table_must_match_its_source_file(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        run_id, source_file_id, _ = _seed_trace(connection)

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                insert_staging_record(
                    connection,
                    run_id=run_id,
                    source_file_id=source_file_id,
                    staging_record_id=uuid4(),
                    source_table="mismatched_table",
                    source_row_number=3,
                )
        transaction.rollback()


def test_error_scopes_require_exact_file_and_row_trace(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        run_id, source_file_id, staging_record_id = _seed_trace(connection)
        file_error_id = uuid4()
        connection.execute(
            ImportError.__table__.insert(),
            {
                "id": file_error_id,
                "import_run_id": run_id,
                "error_scope": "file",
                "import_source_file_id": source_file_id,
                "source_table": "legacy_records",
                "error_code": "SYNTHETIC_FILE_ERROR",
                "error_message": "Synthetic file error",
            },
        )
        stored_file_id = connection.scalar(
            ImportError.__table__.select()
            .with_only_columns(ImportError.import_source_file_id)
            .where(ImportError.id == file_error_id)
        )
        assert stored_file_id == source_file_id

        base_error = {
            "id": uuid4(),
            "import_run_id": run_id,
            "error_scope": "file",
            "import_source_file_id": source_file_id,
            "source_table": "mismatched_table",
            "error_code": "SYNTHETIC_MISMATCH",
            "error_message": "Synthetic mismatch",
        }
        _assert_insert_rejected(connection, ImportError.__table__, base_error)
        _assert_insert_rejected(
            connection,
            ImportError.__table__,
            {
                **base_error,
                "id": uuid4(),
                "error_scope": "row",
                "source_table": "legacy_records",
                "import_staging_record_id": staging_record_id,
                "source_row_number": 3,
            },
        )
        _assert_insert_rejected(
            connection,
            ImportError.__table__,
            {
                **base_error,
                "id": uuid4(),
                "error_scope": "row",
                "source_table": "legacy_records",
                "source_row_number": 2,
                "import_staging_record_id": None,
            },
        )
        transaction.rollback()


def test_mapping_trace_mismatches_and_blank_identity_are_rejected(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        run_id, _, staging_record_id = _seed_trace(connection)
        mapping = {
            "id": uuid4(),
            "import_run_id": run_id,
            "import_staging_record_id": staging_record_id,
            "source_system": "synthetic_legacy",
            "source_table": "legacy_records",
            "source_row_number": 2,
            "source_key": "synthetic-key-001",
            "target_table": "future_entities",
            "mapping_slot": "primary",
            "target_id": uuid4(),
        }
        for mismatch in (
            {"source_system": "wrong_system"},
            {"source_table": "wrong_table"},
            {"source_row_number": 3},
            {"source_key": "wrong-key"},
            {"mapping_slot": "   "},
        ):
            _assert_insert_rejected(
                connection,
                LegacyMapping.__table__,
                {**mapping, "id": uuid4(), **mismatch},
            )
        transaction.rollback()


def test_staging_allows_null_and_repeated_keys_on_different_rows(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        run_id, source_file_id, _ = _seed_trace(connection)
        for row_number, source_key in (
            (3, None),
            (4, None),
            (5, "repeated-key"),
            (6, "repeated-key"),
        ):
            insert_staging_record(
                connection,
                run_id=run_id,
                source_file_id=source_file_id,
                staging_record_id=uuid4(),
                source_row_number=row_number,
                source_key=source_key,
            )
        transaction.rollback()


def test_invalid_status_counts_hash_and_ignored_note_are_rejected(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        run_id, source_file_id, _ = _seed_trace(connection)
        run_values = {
            "id": uuid4(),
            "source_system": "synthetic_legacy",
            "source_manifest_sha256": "d" * 64,
            "importer_version": "test-only-v1",
        }
        _assert_insert_rejected(
            connection, ImportRun.__table__, {**run_values, "status": "unknown"}
        )
        _assert_insert_rejected(
            connection,
            ImportRun.__table__,
            {**run_values, "id": uuid4(), "source_data_row_count": -1},
        )
        file_values = {
            "id": uuid4(),
            "import_run_id": run_id,
            "source_relative_path": "tables/invalid.csv",
            "source_table": "invalid_records",
            "content_sha256": "not-a-hash",
        }
        _assert_insert_rejected(connection, ImportSourceFile.__table__, file_values)
        _assert_insert_rejected(
            connection,
            ImportSourceFile.__table__,
            {
                **file_values,
                "id": uuid4(),
                "content_sha256": "e" * 64,
                "physical_line_count": -1,
            },
        )
        _assert_insert_rejected(
            connection,
            ImportError.__table__,
            {
                "id": uuid4(),
                "import_run_id": run_id,
                "error_scope": "file",
                "import_source_file_id": source_file_id,
                "source_table": "legacy_records",
                "error_code": "SYNTHETIC_IGNORED",
                "error_message": "Synthetic ignored error",
                "resolution_status": "ignored",
                "resolution_note": "   ",
                "resolved_at": datetime.now(UTC),
            },
        )
        transaction.rollback()


def test_parent_run_and_source_file_deletes_are_restricted(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        run_id, source_file_id, _ = _seed_trace(connection)

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    ImportSourceFile.__table__.delete().where(
                        ImportSourceFile.id == source_file_id
                    )
                )
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    ImportRun.__table__.delete().where(ImportRun.id == run_id)
                )
        transaction.rollback()
