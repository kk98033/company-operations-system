"""Nested customer work-item endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import KeywordParams, PageParams, build_list_response
from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.customers.schemas import CustomerStatus
from app.modules.customers.work_item_schemas import (
    WorkItemCreate,
    WorkItemFilters,
    WorkItemListResponse,
    WorkItemResponse,
    WorkItemSortParams,
    WorkItemStatusUpdate,
    WorkItemUpdate,
)
from app.modules.customers.work_item_service import (
    WorkItemCodeConflictError,
    WorkItemConflictError,
    WorkItemNotFoundError,
    create_work_item,
    list_work_items,
    set_work_item_status,
    update_work_item,
)
from app.modules.organizations.scope import OrganizationScope

_read = require_capability("customers.read")
_manage = require_capability("customers.manage")


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, WorkItemNotFoundError):
        raise ApplicationError(
            status_code=404, code="CUSTOMER_WORK_ITEM_NOT_FOUND", message="找不到客戶或常用工作項目"
        ) from None
    if isinstance(error, WorkItemCodeConflictError):
        raise ApplicationError(
            status_code=409, code="CUSTOMER_WORK_ITEM_CODE_CONFLICT", message="工作項目代號已被使用"
        ) from None
    raise ApplicationError(
        status_code=409,
        code="CUSTOMER_WORK_ITEM_UPDATE_CONFLICT",
        message="工作項目已被其他人更新，請重新載入",
    ) from None


def build_work_item_router() -> APIRouter:
    router = APIRouter(prefix="/customers/{customer_id}/work-items", tags=["customers"])

    @router.get("", response_model=WorkItemListResponse, operation_id="customer_work_item_list")
    def work_item_list(
        customer_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_read)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[CustomerStatus | None, Query(alias="status")] = None,
    ) -> WorkItemListResponse:
        try:
            items, total = list_work_items(
                database_session,
                scope=_scope(context),
                customer_id=customer_id,
                page=page,
                keyword=keyword.keyword,
                status=status_filter,
            )
        except WorkItemNotFoundError as error:
            _translate(error)
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=WorkItemSortParams(),
            filters=WorkItemFilters(keyword=keyword.keyword, status=status_filter),
        )
        return WorkItemListResponse.model_validate(response.model_dump())

    @router.post(
        "",
        response_model=WorkItemResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="customer_work_item_create",
    )
    def work_item_create(
        customer_id: UUID,
        payload: WorkItemCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> WorkItemResponse:
        try:
            return create_work_item(
                database_session,
                scope=_scope(context),
                customer_id=customer_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except (WorkItemNotFoundError, WorkItemCodeConflictError) as error:
            _translate(error)

    @router.put(
        "/{item_id}", response_model=WorkItemResponse, operation_id="customer_work_item_update"
    )
    def work_item_update(
        customer_id: UUID,
        item_id: UUID,
        payload: WorkItemUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> WorkItemResponse:
        try:
            return update_work_item(
                database_session,
                scope=_scope(context),
                customer_id=customer_id,
                item_id=item_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except (WorkItemNotFoundError, WorkItemCodeConflictError, WorkItemConflictError) as error:
            _translate(error)

    @router.put(
        "/{item_id}/status",
        response_model=WorkItemResponse,
        operation_id="customer_work_item_status_update",
    )
    def work_item_status(
        customer_id: UUID,
        item_id: UUID,
        payload: WorkItemStatusUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> WorkItemResponse:
        try:
            return set_work_item_status(
                database_session,
                scope=_scope(context),
                customer_id=customer_id,
                item_id=item_id,
                status=payload.status,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except (WorkItemNotFoundError, WorkItemConflictError) as error:
            _translate(error)

    return router
