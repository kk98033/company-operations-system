"""Persist aggregate-only full dry-run trace data without staging source rows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.database.model_registry import REGISTERED_MODELS  # noqa: F401
from app.modules.imports.models import ImportError, ImportRun, ImportSourceFile


class FullDryRunRegistrationError(ValueError):
    """Raised when a report cannot be registered safely."""


def assert_fresh_database(session: Session) -> None:
    """Require every application table to be empty before the integrated rehearsal."""

    populated = []
    for table in Base.metadata.sorted_tables:
        first_column = next(iter(table.c))
        if session.execute(select(first_column).limit(1)).first() is not None:
            populated.append(table.name)
    if populated:
        raise FullDryRunRegistrationError(
            "Phase 10.2 requires a fresh isolated database; application tables are not empty."
        )


def register_full_dry_run(
    session: Session,
    *,
    freeze_report: dict[str, Any],
    full_report: dict[str, Any],
    run_id: UUID | None = None,
) -> UUID:
    """Register one aggregate rehearsal and its source identities in one transaction."""

    source_files = freeze_report.get("source_files")
    summary = full_report.get("summary")
    blockers = full_report.get("high_risk_blockers")
    if (
        not isinstance(source_files, list)
        or not isinstance(summary, dict)
        or not isinstance(blockers, list)
        or full_report.get("apply_performed") is not False
        or full_report.get("ready_for_apply") is not False
        or full_report.get("source_manifest_sha256")
        != freeze_report.get("source_manifest_sha256")
        or full_report.get("importer_fingerprint_sha256")
        != freeze_report.get("importer_fingerprint_sha256")
    ):
        raise FullDryRunRegistrationError("Full dry-run report does not match the frozen contract.")
    if len(source_files) != summary.get("source_file_count"):
        raise FullDryRunRegistrationError("Full dry-run source count does not match the freeze.")

    identifier = run_id or uuid4()
    session.add(
        ImportRun(
            id=identifier,
            source_system=freeze_report["source_system"],
            source_manifest_sha256=freeze_report["source_manifest_sha256"],
            importer_version=freeze_report["importer_fingerprint_sha256"],
            status="awaiting_approval",
            source_data_row_count=summary["source_data_row_count"],
            staged_row_count=0,
            mapped_row_count=0,
            error_count=len(blockers),
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
    )
    session.flush()
    for item in source_files:
        session.add(
            ImportSourceFile(
                import_run_id=identifier,
                source_relative_path=item["relative_path"],
                source_table=item["source_table"],
                content_sha256=item["content_sha256"],
                encoding_name="utf-8-sig" if item.get("valid_utf8") else None,
                file_size_bytes=item["size_bytes"],
                physical_line_count=item["physical_line_count"],
                logical_row_count_including_header=item[
                    "logical_row_count_including_header"
                ],
                data_row_count=item["data_row_count"],
            )
        )
    for blocker in blockers:
        session.add(
            ImportError(
                import_run_id=identifier,
                error_scope="run",
                error_code=blocker["code"],
                error_message="Aggregate dry-run blocker requires resolution before apply.",
                raw_value={"count": blocker["count"], "severity": blocker["severity"]},
                resolution_status="open",
            )
        )
    session.flush()
    return identifier
