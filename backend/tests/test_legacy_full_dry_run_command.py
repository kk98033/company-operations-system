"""Safety tests for the isolated Phase 10.2 command."""

from pathlib import Path

import pytest

from app.core.config import AppSettings
from app.modules.imports.services.full_dry_run_registry import FullDryRunRegistrationError
from scripts import run_legacy_full_dry_run as command
from tests.settings_factory import database_url_for


def test_non_test_environment_is_rejected_before_source_or_database_access(tmp_path: Path) -> None:
    settings = AppSettings.model_validate(
        {
            "APP_ENV": "production",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "8000",
            "DATABASE_URL": database_url_for("production", "company_system_prod"),
            "APP_PUBLIC_ORIGIN": "https://company.example",
            "CSRF_HMAC_KEY": "dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE",
            "AUTH_SECURITY_HMAC_KEY": "dGVzdC1vbmx5LWF1dGgta2V5LTMyLWJ5dGVzISEhISE",
        }
    )
    schema_called = resources_called = builder_called = False

    def forbidden_builder(*args, **kwargs):
        nonlocal builder_called
        builder_called = True
        raise AssertionError

    def forbidden_schema() -> None:
        nonlocal schema_called
        schema_called = True
        raise AssertionError

    def forbidden_resources(*args, **kwargs):
        nonlocal resources_called
        resources_called = True
        raise AssertionError

    with pytest.raises(FullDryRunRegistrationError):
        command.run_full_dry_run_command(
            settings,
            source_dir=tmp_path / "source",
            freeze_report_file=tmp_path / "freeze.json",
            output_file=tmp_path / "report.json",
            report_builder=forbidden_builder,
            schema_upgrader=forbidden_schema,
            resources_factory=forbidden_resources,
        )

    assert not schema_called and not resources_called and not builder_called
