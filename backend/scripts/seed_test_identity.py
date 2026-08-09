"""Explicit CLI for synthetic development/test identities."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from getpass import getpass
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import SecretStr

from app.core.config import AppSettings, SettingsLoadError, load_settings
from app.core.database import DatabaseResources, create_database_resources
from app.seeds.test_identity import (
    SeedConflictError,
    SeedResult,
    SeedSafetyError,
    ensure_seed_environment,
    seed_test_identity,
    validate_seed_passwords,
)

_ADMIN_PASSWORD_VARIABLE = "TEST_ADMIN_SEED_PASSWORD"
_OPERATOR_PASSWORD_VARIABLE = "TEST_OPERATOR_SEED_PASSWORD"
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def upgrade_schema() -> None:
    """Bring the selected non-production database to the current schema head."""

    command.upgrade(Config(str(_BACKEND_ROOT / "alembic.ini")), "head")


def load_seed_passwords(
    environ: Mapping[str, str],
    *,
    prompt: Callable[[str], str] | None,
) -> tuple[SecretStr, SecretStr]:
    """Load secrets without command-line arguments or committed defaults."""

    values: list[SecretStr] = []
    for variable_name, label in (
        (_ADMIN_PASSWORD_VARIABLE, "測試管理員密碼"),
        (_OPERATOR_PASSWORD_VARIABLE, "測試操作員密碼"),
    ):
        raw_value = environ.get(variable_name)
        if raw_value is None and prompt is not None:
            raw_value = prompt(f"{label}（輸入不會顯示）: ")
        if raw_value is None:
            raise SeedSafetyError(f"缺少 {variable_name}；非互動環境必須明確提供")
        values.append(SecretStr(raw_value))
    return values[0], values[1]


def run_seed_command(
    settings: AppSettings,
    *,
    admin_password: SecretStr,
    operator_password: SecretStr,
    schema_upgrader: Callable[[], None] = upgrade_schema,
    resources_factory: Callable[[AppSettings], DatabaseResources] = (
        create_database_resources
    ),
) -> SeedResult:
    """Guard production before constructing database resources."""

    ensure_seed_environment(settings.environment)
    validate_seed_passwords(admin_password, operator_password)
    schema_upgrader()
    resources = resources_factory(settings)
    try:
        with resources.session_factory() as session:
            return seed_test_identity(
                session,
                environment=settings.environment,
                admin_password=admin_password,
                operator_password=operator_password,
            )
    finally:
        resources.dispose()


def main() -> int:
    """Seed synthetic identities and print only a non-sensitive summary."""

    try:
        settings = load_settings()
        ensure_seed_environment(settings.environment)
        prompt = getpass if sys.stdin.isatty() else None
        admin_password, operator_password = load_seed_passwords(
            os.environ,
            prompt=prompt,
        )
        result = run_seed_command(
            settings,
            admin_password=admin_password,
            operator_password=operator_password,
        )
    except (SeedConflictError, SeedSafetyError, SettingsLoadError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception:
        print(
            "虛構測試帳號 seed 執行失敗；請檢查資料庫狀態與 migration",
            file=sys.stderr,
        )
        return 3

    print(
        "Synthetic identity seed complete: "
        f"organizations +{result.created_organizations}, "
        f"users +{result.created_users}, memberships +{result.created_memberships}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
