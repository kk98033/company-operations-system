"""Work-order CRUD and lifecycle HTTP endpoints."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.contracts import KeywordParams, PageParams, build_list_response
from app.core.database.session import get_database_session
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.work_orders.api_common import (
    WORK_ORDER_DOMAIN_ERRORS,
    organization_scope,
    translate_work_order_error,
)
from app.modules.work_orders.lifecycle import (
    clone_work_order,
    confirm_work_order,
    void_work_order,
)
from app.modules.work_orders.schemas import (
    VersionRequest,
    VoidRequest,
    WorkOrderCreate,
    WorkOrderFilters,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderSortParams,
    WorkOrderStatus,
    WorkOrderUpdate,
)
from app.modules.work_orders.service import (
    create_work_order,
    get_work_order,
    list_work_orders,
    update_work_order,
)

_order_read = require_capability("work_orders.read")
_order_manage = require_capability("work_orders.manage")
_order_confirm = require_capability("work_orders.confirm")


def build_work_order_crud_router() -> APIRouter:
    router = APIRouter(prefix="/work-orders", tags=["work-orders"])

    @router.get("", response_model=WorkOrderListResponse, operation_id="work_order_list")
    def work_order_list(
        context: Annotated[AuthenticatedSession, Depends(_order_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[WorkOrderStatus | None, Query(alias="status")] = None,
    ) -> WorkOrderListResponse:
        items, total = list_work_orders(
            session,
            scope=organization_scope(context),
            page=page,
            keyword=keyword.keyword,
            status=status_filter,
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=WorkOrderSortParams(),
            filters=WorkOrderFilters(keyword=keyword.keyword, status=status_filter),
        )
        return WorkOrderListResponse.model_validate(response.model_dump())

    @router.get("/{work_order_id}", response_model=WorkOrderResponse, operation_id="work_order_get")
    def work_order_get(
        work_order_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_order_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> WorkOrderResponse:
        try:
            return get_work_order(
                session, scope=organization_scope(context), work_order_id=work_order_id
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post(
        "", response_model=WorkOrderResponse, status_code=201, operation_id="work_order_create"
    )
    def work_order_create(
        payload: WorkOrderCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> WorkOrderResponse:
        try:
            return create_work_order(
                session,
                scope=organization_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.put(
        "/{work_order_id}", response_model=WorkOrderResponse, operation_id="work_order_update"
    )
    def work_order_update(
        work_order_id: UUID,
        payload: WorkOrderUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> WorkOrderResponse:
        try:
            return update_work_order(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post(
        "/{work_order_id}/confirm",
        response_model=WorkOrderResponse,
        operation_id="work_order_confirm",
    )
    def work_order_confirm(
        work_order_id: UUID,
        payload: VersionRequest,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_confirm)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> WorkOrderResponse:
        try:
            return confirm_work_order(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post(
        "/{work_order_id}/clone",
        response_model=WorkOrderResponse,
        status_code=201,
        operation_id="work_order_clone",
    )
    def work_order_clone(
        work_order_id: UUID,
        order_date: date,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> WorkOrderResponse:
        try:
            return clone_work_order(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                order_date=order_date,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post(
        "/{work_order_id}/void", response_model=WorkOrderResponse, operation_id="work_order_void"
    )
    def work_order_void(
        work_order_id: UUID,
        payload: VoidRequest,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_confirm)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> WorkOrderResponse:
        try:
            return void_work_order(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                expected_updated_at=payload.expected_updated_at,
                reason=payload.reason,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    return router
