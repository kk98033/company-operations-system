"""PostgreSQL evidence for aggregate-only Phase 10.2 registration."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.modules.imports.models import ImportError, ImportRun, ImportSourceFile
from app.modules.imports.services.full_dry_run_registry import (
    FullDryRunRegistrationError,
    assert_fresh_database,
    register_full_dry_run,
)

pytestmark = pytest.mark.database_integration


def _freeze() -> dict:
    return {
        "source_system": "synthetic",
        "source_manifest_sha256": "a" * 64,
        "importer_fingerprint_sha256": "b" * 64,
        "source_files": [
            {
                "relative_path": "one.csv",
                "source_table": "one",
                "content_sha256": "c" * 64,
                "valid_utf8": True,
                "size_bytes": 12,
                "physical_line_count": 2,
                "logical_row_count_including_header": 2,
                "data_row_count": 1,
            },
            {
                "relative_path": "two.csv",
                "source_table": "two",
                "content_sha256": "d" * 64,
                "valid_utf8": True,
                "size_bytes": 14,
                "physical_line_count": 3,
                "logical_row_count_including_header": 3,
                "data_row_count": 2,
            },
        ],
    }


def _report() -> dict:
    return {
        "source_manifest_sha256": "a" * 64,
        "importer_fingerprint_sha256": "b" * 64,
        "summary": {"source_file_count": 2, "source_data_row_count": 3},
        "high_risk_blockers": [
            {"code": "SYNTHETIC_BLOCKER", "count": 2, "severity": "high"}
        ],
        "ready_for_apply": False,
        "apply_performed": False,
    }


def test_registers_manifest_and_blockers_without_business_or_staging_rows(
    migrated_engine: Engine,
) -> None:
    run_id = uuid4()
    try:
        with Session(migrated_engine) as session, session.begin():
            assert_fresh_database(session)
            assert register_full_dry_run(
                session, freeze_report=_freeze(), full_report=_report(), run_id=run_id
            ) == run_id

        with Session(migrated_engine) as session:
            run = session.get(ImportRun, run_id)
            assert run is not None
            assert run.status == "awaiting_approval"
            assert run.source_data_row_count == 3
            assert run.staged_row_count == 0
            assert run.mapped_row_count == 0
            assert run.error_count == 1
            assert session.scalar(
                select(func.count()).select_from(ImportSourceFile).where(
                    ImportSourceFile.import_run_id == run_id
                )
            ) == 2
            error = session.scalar(
                select(ImportError).where(ImportError.import_run_id == run_id)
            )
            assert error is not None
            assert error.raw_value == {"count": 2, "severity": "high"}
            with pytest.raises(FullDryRunRegistrationError):
                assert_fresh_database(session)
    finally:
        with migrated_engine.begin() as connection:
            connection.execute(ImportError.__table__.delete().where(ImportError.import_run_id == run_id))
            connection.execute(
                ImportSourceFile.__table__.delete().where(ImportSourceFile.import_run_id == run_id)
            )
            connection.execute(ImportRun.__table__.delete().where(ImportRun.id == run_id))
