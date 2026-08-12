"""Safety contract for the explicit synthetic identity seed command."""

from secrets import token_urlsafe

import pytest
from pydantic import SecretStr

from app.core.config import AppSettings
from app.seeds.test_identity import SeedResult, SeedSafetyError
from scripts import seed_test_identity as seed_command
from tests.settings_factory import database_url_for, make_test_settings


def test_production_is_rejected_before_resource_factory_is_called() -> None:
    settings = AppSettings.model_validate(
        {
            "APP_ENV": "production",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": "8000",
            "DATABASE_URL": database_url_for(
                "production",
                "company_system_prod",
            ),
            "APP_PUBLIC_ORIGIN": "https://company.example",
            "CSRF_HMAC_KEY": "dGVzdC1vbmx5LWNzcmYta2V5LTMyLWJ5dGVzISEhISE",
            "AUTH_SECURITY_HMAC_KEY": "dGVzdC1vbmx5LWF1dGgta2V5LTMyLWJ5dGVzISEhISE",
        }
    )
    resource_factory_called = False
    schema_upgrader_called = False

    def forbidden_schema_upgrader() -> None:
        nonlocal schema_upgrader_called
        schema_upgrader_called = True
        raise AssertionError("production must not run migrations")

    def forbidden_resource_factory(_: AppSettings):
        nonlocal resource_factory_called
        resource_factory_called = True
        raise AssertionError("production must not create database resources")

    with pytest.raises(SeedSafetyError):
        seed_command.run_seed_command(
            settings,
            admin_password=SecretStr(token_urlsafe(24)),
            operator_password=SecretStr(token_urlsafe(24)),
            schema_upgrader=forbidden_schema_upgrader,
            resources_factory=forbidden_resource_factory,
        )

    assert schema_upgrader_called is False
    assert resource_factory_called is False


@pytest.mark.parametrize(
    "admin_password,operator_password",
    [
        ("", token_urlsafe(24)),
        ("too-short", token_urlsafe(24)),
        ("replace-with-test-password", token_urlsafe(24)),
        ("x" * 257, token_urlsafe(24)),
        ("same-synthetic-secret", "same-synthetic-secret"),
    ],
)
def test_invalid_secrets_are_rejected_before_resource_factory_is_called(
    admin_password: str,
    operator_password: str,
) -> None:
    resource_factory_called = False
    schema_upgrader_called = False

    def forbidden_schema_upgrader() -> None:
        nonlocal schema_upgrader_called
        schema_upgrader_called = True
        raise AssertionError("invalid secrets must not run migrations")

    def forbidden_resource_factory(_: AppSettings):
        nonlocal resource_factory_called
        resource_factory_called = True
        raise AssertionError("invalid secrets must not create database resources")

    with pytest.raises(SeedSafetyError) as error:
        seed_command.run_seed_command(
            make_test_settings(),
            admin_password=SecretStr(admin_password),
            operator_password=SecretStr(operator_password),
            schema_upgrader=forbidden_schema_upgrader,
            resources_factory=forbidden_resource_factory,
        )

    assert schema_upgrader_called is False
    assert resource_factory_called is False
    for raw_password in {admin_password, operator_password}:
        if raw_password:
            assert raw_password not in str(error.value)


def test_noninteractive_secret_loading_requires_both_named_variables() -> None:
    sentinel = token_urlsafe(24)

    with pytest.raises(SeedSafetyError) as error:
        seed_command.load_seed_passwords(
            {"TEST_ADMIN_SEED_PASSWORD": sentinel},
            prompt=None,
        )

    assert "TEST_OPERATOR_SEED_PASSWORD" in str(error.value)
    assert sentinel not in str(error.value)


def test_main_prints_only_non_sensitive_seed_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    admin_password = token_urlsafe(24)
    operator_password = token_urlsafe(24)
    monkeypatch.setenv("TEST_ADMIN_SEED_PASSWORD", admin_password)
    monkeypatch.setenv("TEST_OPERATOR_SEED_PASSWORD", operator_password)
    monkeypatch.setattr(seed_command, "load_settings", make_test_settings)
    monkeypatch.setattr(
        seed_command,
        "run_seed_command",
        lambda *args, **kwargs: SeedResult(1, 2, 2),
    )

    assert seed_command.main() == 0
    captured = capsys.readouterr()
    assert "organizations +1, users +2, memberships +2" in captured.out
    assert captured.err == ""
    assert admin_password not in captured.out
    assert operator_password not in captured.out
    assert "$argon2" not in captured.out


def test_main_masks_unexpected_exception_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    admin_password = token_urlsafe(24)
    operator_password = token_urlsafe(24)
    exception_sentinel = token_urlsafe(24)
    monkeypatch.setenv("TEST_ADMIN_SEED_PASSWORD", admin_password)
    monkeypatch.setenv("TEST_OPERATOR_SEED_PASSWORD", operator_password)
    monkeypatch.setattr(seed_command, "load_settings", make_test_settings)

    def raise_unexpected_error(*args, **kwargs):
        raise RuntimeError(exception_sentinel)

    monkeypatch.setattr(seed_command, "run_seed_command", raise_unexpected_error)

    assert seed_command.main() == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "seed 執行失敗" in captured.err
    assert exception_sentinel not in captured.err
    assert admin_password not in captured.err
    assert operator_password not in captured.err
