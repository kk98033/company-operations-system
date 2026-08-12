"""Shared HTTP helpers for master data."""

from typing import NoReturn

from app.core.errors import ApplicationError
from app.modules.auth.services import AuthenticatedSession
from app.modules.master_data.errors import MasterDuplicateError, MasterNotFoundError
from app.modules.organizations.scope import OrganizationScope


def master_scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def translate_master_error(error: Exception) -> NoReturn:
    if isinstance(error, MasterNotFoundError):
        raise ApplicationError(
            status_code=404, code="MASTER_DATA_NOT_FOUND", message="找不到主檔資料"
        ) from None
    if isinstance(error, MasterDuplicateError):
        raise ApplicationError(
            status_code=409, code="MASTER_DATA_DUPLICATE", message="代號或名稱已被使用"
        ) from None
    raise ApplicationError(
        status_code=409,
        code="MASTER_DATA_UPDATE_CONFLICT",
        message="主檔資料已被其他人更新，請重新載入",
    ) from None
