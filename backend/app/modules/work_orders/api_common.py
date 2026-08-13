"""Shared HTTP translation for the work-order module."""

from typing import NoReturn

from app.core.errors import ApplicationError
from app.modules.auth.services import AuthenticatedSession
from app.modules.organizations.scope import OrganizationScope
from app.modules.work_orders.errors import (
    AttachmentValidationError,
    QuotationConversionError,
    WorkOrderConflictError,
    WorkOrderNotFoundError,
    WorkOrderNumberExhaustedError,
    WorkOrderStateError,
)

WORK_ORDER_DOMAIN_ERRORS = (
    AttachmentValidationError,
    QuotationConversionError,
    WorkOrderConflictError,
    WorkOrderNotFoundError,
    WorkOrderNumberExhaustedError,
    WorkOrderStateError,
)


def organization_scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def translate_work_order_error(error: Exception) -> NoReturn:
    if isinstance(error, WorkOrderNotFoundError):
        raise ApplicationError(
            status_code=404, code="WORK_ORDER_NOT_FOUND", message="找不到案件或工單資料"
        ) from None
    if isinstance(error, WorkOrderNumberExhaustedError):
        raise ApplicationError(
            status_code=409,
            code="WORK_ORDER_NUMBER_EXHAUSTED",
            message="當日案件或工單號碼已用完",
        ) from None
    if isinstance(error, WorkOrderStateError):
        raise ApplicationError(
            status_code=409,
            code="WORK_ORDER_STATE_CONFLICT",
            message="目前狀態不允許此操作",
        ) from None
    if isinstance(error, QuotationConversionError):
        raise ApplicationError(
            status_code=409,
            code="QUOTATION_CONVERSION_INVALID",
            message="報價尚未確認、明細不符或無法轉換",
        ) from None
    if isinstance(error, AttachmentValidationError):
        raise ApplicationError(
            status_code=422,
            code="ATTACHMENT_INVALID",
            message="附件僅接受 5MB 內的 JPG、PNG、WebP 或 PDF",
        ) from None
    raise ApplicationError(
        status_code=409,
        code="WORK_ORDER_UPDATE_CONFLICT",
        message="資料已被更新，請重新載入",
    ) from None
