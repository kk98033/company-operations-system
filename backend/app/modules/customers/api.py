"""Customer master HTTP endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import KeywordParams, PageParams, SortDirection, build_list_response
from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.customers.schemas import (
    CustomerCreate,
    CustomerFilterSummary,
    CustomerListResponse,
    CustomerResponse,
    CustomerSortField,
    CustomerSortParams,
    CustomerStatus,
    CustomerStatusUpdate,
    CustomerUpdate,
)
from app.modules.customers.service import (
    CustomerCodeConflictError,
    CustomerConflictError,
    CustomerNotFoundError,
    create_customer,
    get_customer,
    list_customers,
    set_customer_status,
    update_customer,
)
from app.modules.organizations.scope import OrganizationScope

_require_read = require_capability("customers.read")
_require_manage = require_capability("customers.manage")


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, CustomerNotFoundError):
        raise ApplicationError(
            status_code=404, code="CUSTOMER_NOT_FOUND", message="找不到客戶資料"
        ) from None
    if isinstance(error, CustomerCodeConflictError):
        raise ApplicationError(
            status_code=409, code="CUSTOMER_CODE_CONFLICT", message="客戶代號已被使用"
        ) from None
    raise ApplicationError(
        status_code=409,
        code="CUSTOMER_UPDATE_CONFLICT",
        message="客戶資料已被其他人更新，請重新載入",
    ) from None


def build_customer_router() -> APIRouter:
    router = APIRouter(prefix="/customers", tags=["customers"])

    @router.get("", response_model=CustomerListResponse, operation_id="customer_list")
    def customer_list(
        context: Annotated[AuthenticatedSession, Depends(_require_read)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[CustomerStatus | None, Query(alias="status")] = None,
        sort_by: Annotated[CustomerSortField, Query()] = CustomerSortField.CODE,
        sort_direction: Annotated[SortDirection, Query()] = SortDirection.ASC,
    ) -> CustomerListResponse:
        sort = CustomerSortParams(sort_by=sort_by, sort_direction=sort_direction)
        items, total = list_customers(
            database_session,
            scope=_scope(context),
            page=page,
            keyword=keyword.keyword,
            status=status_filter,
            sort=sort,
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=sort,
            filters=CustomerFilterSummary(keyword=keyword.keyword, status=status_filter),
        )
        return CustomerListResponse.model_validate(response.model_dump())

    @router.get("/{customer_id}", response_model=CustomerResponse, operation_id="customer_get")
    def customer_get(
        customer_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_require_read)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CustomerResponse:
        try:
            return get_customer(database_session, scope=_scope(context), customer_id=customer_id)
        except CustomerNotFoundError as error:
            _translate(error)

    @router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED, operation_id="customer_create")
    def customer_create(
        payload: CustomerCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_require_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CustomerResponse:
        try:
            return create_customer(database_session, scope=_scope(context), payload=payload, request_id=require_request_id(request))
        except CustomerCodeConflictError as error:
            _translate(error)

    @router.put("/{customer_id}", response_model=CustomerResponse, operation_id="customer_update")
    def customer_update(
        customer_id: UUID,
        payload: CustomerUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_require_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CustomerResponse:
        try:
            return update_customer(database_session, scope=_scope(context), customer_id=customer_id, payload=payload, request_id=require_request_id(request))
        except (CustomerNotFoundError, CustomerCodeConflictError, CustomerConflictError) as error:
            _translate(error)

    @router.put("/{customer_id}/status", response_model=CustomerResponse, operation_id="customer_status_update")
    def customer_status_update(
        customer_id: UUID,
        payload: CustomerStatusUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_require_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        database_session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CustomerResponse:
        try:
            return set_customer_status(
                database_session,
                scope=_scope(context),
                customer_id=customer_id,
                status=payload.status,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except (CustomerNotFoundError, CustomerConflictError) as error:
            _translate(error)

    return router
