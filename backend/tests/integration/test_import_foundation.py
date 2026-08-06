"""PostgreSQL acceptance tests for traceability and import idempotency."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError

from app.modules.imports.models import (
    ImportError,
    ImportRun,
    ImportStagingRecord,
    LegacyMapping,
)
from tests.integration.synthetic_import_data import (
    insert_import_run,
    insert_staged_source,
)

pytestmark = [
    pytest.mark.database_integration,
    pytest.mark.skipif(
        os.getenv("RUN_DATABASE_INTEGRATION") != "1",
        reason="requires explicit isolated PostgreSQL integration run",
    ),
]


def test_migrated_schema_has_expected_constraints_and_indexes(
    migrated_engine: Engine,
) -> None:
    database_inspector = inspect(migrated_engine)
    staging_uniques = database_inspector.get_unique_constraints(
        "import_staging_records"
    )
    mapping_uniques = database_inspector.get_unique_constraints("legacy_mappings")

    assert any(
        unique["column_names"] == ["import_source_file_id", "source_row_number"]
        for unique in staging_uniques
    )
    assert any(
        unique["column_names"]
        == [
            "source_system",
            "source_table",
            "source_key",
            "target_table",
            "mapping_slot",
        ]
        for unique in mapping_uniques
    )
    assert {
        index["name"]
        for index in database_inspector.get_indexes("import_errors")
    } >= {
        "ix_import_errors_import_run_id_resolution_status",
        "ix_import_errors_run_table_source_row_number",
    }
    assert "ix_import_source_files_source_table_content_sha256" in {
        index["name"]
        for index in database_inspector.get_indexes("import_source_files")
    }


def test_same_source_can_rerun_but_mapping_identity_cannot_duplicate(
    migrated_engine: Engine,
) -> None:
    run_one_id = uuid4()
    run_two_id = uuid4()
    staging_one_id = uuid4()
    staging_two_id = uuid4()
    target_one_id = uuid4()

    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        for run_id in (run_one_id, run_two_id):
            insert_import_run(connection, run_id)
        insert_staged_source(
            connection,
            run_id=run_one_id,
            source_file_id=uuid4(),
            staging_record_id=staging_one_id,
        )
        insert_staged_source(
            connection,
            run_id=run_two_id,
            source_file_id=uuid4(),
            staging_record_id=staging_two_id,
        )

        mapping_values = {
            "id": uuid4(),
            "import_run_id": run_one_id,
            "import_staging_record_id": staging_one_id,
            "source_system": "synthetic_legacy",
            "source_table": "legacy_records",
            "source_row_number": 2,
            "source_key": "synthetic-key-001",
            "target_table": "future_entities",
            "mapping_slot": "primary",
            "target_id": target_one_id,
        }
        connection.execute(LegacyMapping.__table__.insert(), mapping_values)
        connection.execute(
            LegacyMapping.__table__.insert(),
            {**mapping_values, "id": uuid4(), "mapping_slot": "child-001"},
        )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    LegacyMapping.__table__.insert(),
                    {
                        **mapping_values,
                        "id": uuid4(),
                        "import_run_id": run_two_id,
                        "import_staging_record_id": staging_two_id,
                        "target_id": uuid4(),
                    },
                )
        transaction.rollback()


def test_staging_and_errors_preserve_traceability_boundaries(
    migrated_engine: Engine,
) -> None:
    run_id = uuid4()
    source_file_id = uuid4()
    staging_record_id = uuid4()

    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        insert_import_run(connection, run_id, manifest_sha256="c" * 64)
        insert_staged_source(
            connection,
            run_id=run_id,
            source_file_id=source_file_id,
            staging_record_id=staging_record_id,
        )

        staged_payload = connection.execute(
            ImportStagingRecord.__table__.select().where(
                ImportStagingRecord.id == staging_record_id
            )
        ).mappings().one()
        assert staged_payload["raw_payload"] == {"legacy_label": "raw canary"}
        assert staged_payload["normalized_payload"] == {
            "display_label": "normalized canary"
        }

        connection.execute(
            ImportError.__table__.insert(),
            {
                "id": uuid4(),
                "import_run_id": run_id,
                "error_scope": "file",
                "import_source_file_id": source_file_id,
                "source_table": "legacy_records",
                "error_code": "SYNTHETIC_FILE_ERROR",
                "error_message": "Synthetic file-level failure",
            },
        )
        connection.execute(
            ImportError.__table__.insert(),
            {
                "id": uuid4(),
                "import_run_id": run_id,
                "error_scope": "field",
                "import_source_file_id": source_file_id,
                "import_staging_record_id": staging_record_id,
                "source_table": "legacy_records",
                "source_row_number": 2,
                "field_name": "legacy_label",
                "error_code": "SYNTHETIC_FIELD_ERROR",
                "error_message": "Synthetic field-level failure",
                "raw_value": "raw canary",
                "resolution_status": "resolved",
                "resolved_at": datetime.now(UTC),
            },
        )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    ImportRun.__table__.insert(),
                    {
                        "id": uuid4(),
                        "source_system": "synthetic_legacy",
                        "source_manifest_sha256": "NOT-A-SHA256",
                        "importer_version": "test-only-v1",
                    },
                )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    ImportError.__table__.insert(),
                    {
                        "id": uuid4(),
                        "import_run_id": run_id,
                        "error_scope": "run",
                        "error_code": "SYNTHETIC_BAD_RESOLUTION",
                        "error_message": "Resolved without a timestamp",
                        "resolution_status": "resolved",
                    },
                )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    ImportStagingRecord.__table__.insert(),
                    {
                        "id": uuid4(),
                        "import_run_id": run_id,
                        "import_source_file_id": source_file_id,
                        "source_table": "legacy_records",
                        "source_row_number": 2,
                        "raw_payload": {"duplicate": True},
                    },
                )
        transaction.rollback()
