"""Idempotent synthetic identities for development and test environments."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import AppEnvironment
from app.modules.auth.models import User
from app.modules.auth.passwords import hash_password, verify_password
from app.modules.organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationSettings,
)
from app.modules.organizations.settings import new_organization_settings

TEST_ORGANIZATION_ID = UUID("10000000-0000-4000-8000-000000000001")
TEST_ADMIN_USER_ID = UUID("20000000-0000-4000-8000-000000000001")
TEST_OPERATOR_USER_ID = UUID("20000000-0000-4000-8000-000000000002")
TEST_ADMIN_MEMBER_ID = UUID("30000000-0000-4000-8000-000000000001")
TEST_OPERATOR_MEMBER_ID = UUID("30000000-0000-4000-8000-000000000002")

TEST_ORGANIZATION_NAME = "測試印刷股份有限公司（虛構）"
TEST_ADMIN_LOGIN_NAME = "test.admin"
TEST_OPERATOR_LOGIN_NAME = "test.operator"
TEST_ADMIN_DISPLAY_NAME = "測試管理員（尚未指派角色）"
TEST_OPERATOR_DISPLAY_NAME = "測試操作員（尚未指派角色）"
_MIN_PASSWORD_LENGTH = 16
_MAX_PASSWORD_LENGTH = 256
_FORBIDDEN_PASSWORD_MARKERS = ("change-me", "password", "replace-with")


class SeedSafetyError(RuntimeError):
    """Safe refusal caused by environment or secret policy."""


class SeedConflictError(RuntimeError):
    """Safe refusal caused by pre-existing incompatible seed identities."""


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Non-sensitive summary of rows created by one seed run."""

    created_organizations: int
    created_users: int
    created_memberships: int


@dataclass(frozen=True, slots=True)
class _UserSeedSpec:
    user_id: UUID
    membership_id: UUID
    login_name: str
    display_name: str
    password: SecretStr


def ensure_seed_environment(environment: AppEnvironment) -> None:
    """Reject production before any engine, connection, or hash work begins."""

    if environment not in {AppEnvironment.DEVELOPMENT, AppEnvironment.TEST}:
        raise SeedSafetyError("虛構測試帳號 seed 只允許 development 或 test 環境")


def _validate_seed_password(variable_name: str, password: SecretStr) -> None:
    raw_password = password.get_secret_value()
    normalized = raw_password.strip().lower()
    if not (_MIN_PASSWORD_LENGTH <= len(raw_password) <= _MAX_PASSWORD_LENGTH):
        raise SeedSafetyError(
            f"{variable_name} 長度必須介於 {_MIN_PASSWORD_LENGTH} 到 "
            f"{_MAX_PASSWORD_LENGTH} 字元"
        )
    if not normalized or any(marker in normalized for marker in _FORBIDDEN_PASSWORD_MARKERS):
        raise SeedSafetyError(f"{variable_name} 不可使用空白或範例密碼")


def validate_seed_passwords(
    admin_password: SecretStr,
    operator_password: SecretStr,
) -> None:
    """Validate both secrets before an engine or transaction is needed."""

    _validate_seed_password("TEST_ADMIN_SEED_PASSWORD", admin_password)
    _validate_seed_password("TEST_OPERATOR_SEED_PASSWORD", operator_password)
    if admin_password.get_secret_value() == operator_password.get_secret_value():
        raise SeedSafetyError("測試管理員與操作員必須使用不同 seed 密碼")


def _ensure_organization(session: Session) -> int:
    organization = session.get(Organization, TEST_ORGANIZATION_ID)
    if organization is None:
        session.add(
            Organization(
                id=TEST_ORGANIZATION_ID,
                name=TEST_ORGANIZATION_NAME,
            )
        )
        return 1
    if organization.name != TEST_ORGANIZATION_NAME or organization.status != "active":
        raise SeedConflictError("固定測試公司 ID 已被不相容資料使用")
    return 0


def _ensure_user(session: Session, spec: _UserSeedSpec) -> int:
    user = session.get(User, spec.user_id)
    login_owner = session.scalar(
        select(User).where(func.lower(func.btrim(User.login_name)) == spec.login_name)
    )
    if login_owner is not None and login_owner.id != spec.user_id:
        raise SeedConflictError("固定測試登入代號已被其他使用者使用")
    if user is None:
        session.add(
            User(
                id=spec.user_id,
                login_name=spec.login_name,
                display_name=spec.display_name,
                password_hash=hash_password(spec.password),
            )
        )
        return 1
    if (
        user.login_name != spec.login_name
        or user.display_name != spec.display_name
        or user.status != "active"
    ):
        raise SeedConflictError("固定測試使用者 ID 已被不相容資料使用")
    if not verify_password(spec.password, user.password_hash):
        raise SeedConflictError("目前 seed 密碼與既有測試帳號不一致")
    return 0


def _ensure_organization_settings(session: Session) -> None:
    settings = session.get(OrganizationSettings, TEST_ORGANIZATION_ID)
    if settings is None:
        session.add(new_organization_settings(TEST_ORGANIZATION_ID))
        return
    if (
        settings.document_number_policy_version != "adr-018-v1"
        or settings.quotation_print_layout_version != "gmail-a4-landscape-v1"
        or settings.work_order_print_layout_version
        != "gmail-a4-portrait-9-process-v1"
    ):
        raise SeedConflictError("固定測試公司的文件政策版本不相容")


def _ensure_membership(session: Session, spec: _UserSeedSpec) -> int:
    membership = session.get(OrganizationMember, spec.membership_id)
    if membership is None:
        session.add(
            OrganizationMember(
                id=spec.membership_id,
                organization_id=TEST_ORGANIZATION_ID,
                user_id=spec.user_id,
            )
        )
        return 1
    if (
        membership.organization_id != TEST_ORGANIZATION_ID
        or membership.user_id != spec.user_id
        or membership.status != "active"
    ):
        raise SeedConflictError("固定測試成員 ID 已被不相容資料使用")
    return 0


def seed_test_identity(
    session: Session,
    *,
    environment: AppEnvironment,
    admin_password: SecretStr,
    operator_password: SecretStr,
) -> SeedResult:
    """Create one synthetic company and two users in one owned transaction."""

    ensure_seed_environment(environment)
    validate_seed_passwords(admin_password, operator_password)
    specs = (
        _UserSeedSpec(
            user_id=TEST_ADMIN_USER_ID,
            membership_id=TEST_ADMIN_MEMBER_ID,
            login_name=TEST_ADMIN_LOGIN_NAME,
            display_name=TEST_ADMIN_DISPLAY_NAME,
            password=admin_password,
        ),
        _UserSeedSpec(
            user_id=TEST_OPERATOR_USER_ID,
            membership_id=TEST_OPERATOR_MEMBER_ID,
            login_name=TEST_OPERATOR_LOGIN_NAME,
            display_name=TEST_OPERATOR_DISPLAY_NAME,
            password=operator_password,
        ),
    )

    try:
        with session.begin():
            created_organizations = _ensure_organization(session)
            session.flush()
            _ensure_organization_settings(session)
            created_users = sum(_ensure_user(session, spec) for spec in specs)
            session.flush()
            created_memberships = sum(
                _ensure_membership(session, spec) for spec in specs
            )
            session.flush()
    except IntegrityError:
        raise SeedConflictError("虛構測試帳號 seed 與既有資料衝突") from None

    return SeedResult(
        created_organizations=created_organizations,
        created_users=created_users,
        created_memberships=created_memberships,
    )
