"""Run Phase 10.2 only against the isolated disposable PostgreSQL database."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values

from app.core.config import AppEnvironment, AppSettings
from app.core.database import DatabaseResources, create_database_resources
from app.modules.imports.services.full_dry_run_registry import (
    FullDryRunRegistrationError,
    assert_fresh_database,
    register_full_dry_run,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
ROOT_SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(ROOT_SCRIPTS))

from legacy_full_dry_run import build_full_report  # noqa: E402


def load_isolated_test_settings() -> AppSettings:
    values = dotenv_values(PROJECT_ROOT / ".env")
    username = values.get("POSTGRES_TEST_USER") or "company_system_test"
    password = values.get("POSTGRES_TEST_PASSWORD") or "company-system-test-only"
    database = values.get("POSTGRES_TEST_DB") or "company_system_test"
    port = values.get("POSTGRES_TEST_PORT") or "5433"
    database_url = (
        f"postgresql+psycopg://{quote(str(username), safe='')}:{quote(str(password), safe='')}"
        f"@127.0.0.1:{port}/{quote(str(database), safe='')}"
    )
    return AppSettings.model_validate(
        {
            "APP_ENV": "test",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "8000",
            "DATABASE_URL": database_url,
            "APP_PUBLIC_ORIGIN": "http://testserver",
            "CSRF_HMAC_KEY": "dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE",
            "AUTH_SECURITY_HMAC_KEY": "dGVzdC1vbmx5LWF1dGgta2V5LTMyLWJ5dGVzISEhISE",
        }
    )


def upgrade_schema() -> None:
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")


def run_full_dry_run_command(
    settings: AppSettings,
    *,
    source_dir: Path,
    freeze_report_file: Path,
    output_file: Path,
    report_builder: Callable[[Path, dict[str, Any]], dict[str, Any]] = build_full_report,
    schema_upgrader: Callable[[], None] = upgrade_schema,
    resources_factory: Callable[[AppSettings], DatabaseResources] = create_database_resources,
) -> tuple[dict[str, Any], str]:
    if settings.environment is not AppEnvironment.TEST:
        raise FullDryRunRegistrationError("Phase 10.2 is restricted to the isolated test database.")
    source_dir = source_dir.resolve()
    output_file = output_file.resolve()
    if not source_dir.is_dir() or output_file == source_dir or source_dir in output_file.parents:
        raise FullDryRunRegistrationError("Dry-run paths do not satisfy the read-only source boundary.")
    freeze_report = json.loads(freeze_report_file.read_text(encoding="utf-8"))
    full_report = report_builder(source_dir, freeze_report)
    schema_upgrader()
    resources = resources_factory(settings)
    try:
        with resources.session_factory() as session, session.begin():
            assert_fresh_database(session)
            run_id = register_full_dry_run(
                session,
                freeze_report=freeze_report,
                full_report=full_report,
            )
    finally:
        resources.dispose()
    full_report["database_registration"] = {
        "import_run_id": str(run_id),
        "status": "awaiting_approval",
        "business_rows_written": 0,
        "staging_rows_written": 0,
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(full_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return full_report, str(run_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--freeze-report", required=True, type=Path)
    parser.add_argument("--output-file", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report, run_id = run_full_dry_run_command(
            load_isolated_test_settings(),
            source_dir=args.source_dir,
            freeze_report_file=args.freeze_report,
            output_file=args.output_file,
        )
    except (FullDryRunRegistrationError, OSError, ValueError, json.JSONDecodeError):
        print("Phase 10.2 full dry-run failed; inspect the isolated test setup.", file=sys.stderr)
        return 2
    except Exception:
        print("Phase 10.2 full dry-run failed safely.", file=sys.stderr)
        return 3
    print(
        "Phase 10.2 aggregate dry-run complete: "
        f"run {run_id}, files {report['summary']['source_file_count']}, "
        f"blockers {report['summary']['high_risk_blocker_count']}, apply false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
