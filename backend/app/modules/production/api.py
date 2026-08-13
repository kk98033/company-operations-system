"""Production supervision, final completion, and inventory HTTP API."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.contracts import KeywordParams, PageParams, build_list_response
from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.completion_service import record_final_completion
from app.modules.production.errors import (
    InventoryInsufficientError,
    ProductionConflictError,
    ProductionNotFoundError,
    ProductionStateError,
)
from app.modules.production.inventory_service import adjust_inventory
from app.modules.production.process_service import record_process_event
from app.modules.production.query_service import (
    get_production_order,
    list_inventory,
    list_production_orders,
)
from app.modules.production.reversal_service import reverse_final_completion
from app.modules.production.schemas import (
    FinalCompletionCreate,
    FinalCompletionResponse,
    InventoryAdjustmentCreate,
    InventoryFilters,
    InventoryLedgerResponse,
    InventoryListResponse,
    InventorySortParams,
    ProcessEventCreate,
    ProcessEventResponse,
    ProductionFilters,
    ProductionOrderDetail,
    ProductionOrderListResponse,
    ProductionSortParams,
    ReversalCreate,
)

_production_read = require_capability("production.read")
_production_manage = require_capability("production.manage")
_production_complete = require_capability("production.complete")
_inventory_read = require_capability("inventory.read")
_inventory_adjust = require_capability("inventory.adjust")
ERRORS = (
    ProductionNotFoundError,
    ProductionStateError,
    ProductionConflictError,
    InventoryInsufficientError,
)


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, ProductionNotFoundError):
        raise ApplicationError(
            status_code=404, code="PRODUCTION_NOT_FOUND", message="找不到生產或庫存資料"
        ) from None
    if isinstance(error, InventoryInsufficientError):
        raise ApplicationError(
            status_code=409,
            code="INVENTORY_INSUFFICIENT",
            message="可用庫存不足，不能留下負庫存",
        ) from None
    if isinstance(error, ProductionStateError):
        raise ApplicationError(
            status_code=409,
            code="PRODUCTION_STATE_CONFLICT",
            message="製程狀態或運送前置條件不符合",
        ) from None
    raise ApplicationError(
        status_code=409,
        code="PRODUCTION_UPDATE_CONFLICT",
        message="資料已被處理，請重新載入",
    ) from None


def build_production_router() -> APIRouter:
    router = APIRouter(tags=["production"])

    @router.get(
        "/production", response_model=ProductionOrderListResponse, operation_id="production_list"
    )
    def production_list(
        context: Annotated[AuthenticatedSession, Depends(_production_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
    ) -> ProductionOrderListResponse:
        items, total = list_production_orders(
            session, scope=_scope(context), page=page, keyword=keyword.keyword
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=ProductionSortParams(),
            filters=ProductionFilters(keyword=keyword.keyword),
        )
        return ProductionOrderListResponse.model_validate(response.model_dump())

    @router.get(
        "/production/work-orders/{work_order_id}",
        response_model=ProductionOrderDetail,
        operation_id="production_get",
    )
    def production_get(
        work_order_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_production_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ProductionOrderDetail:
        try:
            return get_production_order(session, scope=_scope(context), work_order_id=work_order_id)
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/production/work-orders/{work_order_id}/process-events",
        response_model=ProcessEventResponse,
        status_code=201,
        operation_id="production_process_event_create",
    )
    def process_event_create(
        work_order_id: UUID,
        payload: ProcessEventCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_production_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ProcessEventResponse:
        try:
            return record_process_event(
                session,
                scope=_scope(context),
                work_order_id=work_order_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/production/work-orders/{work_order_id}/final-completions",
        response_model=FinalCompletionResponse,
        status_code=201,
        operation_id="production_final_completion_create",
    )
    def final_completion_create(
        work_order_id: UUID,
        payload: FinalCompletionCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_production_complete)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> FinalCompletionResponse:
        try:
            return record_final_completion(
                session,
                scope=_scope(context),
                work_order_id=work_order_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/production/final-completions/{entry_id}/reverse",
        response_model=FinalCompletionResponse,
        status_code=201,
        operation_id="production_final_completion_reverse",
    )
    def final_completion_reverse(
        entry_id: UUID,
        payload: ReversalCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_production_complete)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> FinalCompletionResponse:
        try:
            return reverse_final_completion(
                session,
                scope=_scope(context),
                entry_id=entry_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get("/inventory", response_model=InventoryListResponse, operation_id="inventory_list")
    def inventory_list(
        context: Annotated[AuthenticatedSession, Depends(_inventory_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        positive_only: Annotated[bool, Query()] = True,
    ) -> InventoryListResponse:
        items, total = list_inventory(
            session,
            scope=_scope(context),
            page=page,
            keyword=keyword.keyword,
            positive_only=positive_only,
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=InventorySortParams(),
            filters=InventoryFilters(keyword=keyword.keyword, positive_only=positive_only),
        )
        return InventoryListResponse.model_validate(response.model_dump())

    @router.get(
        "/inventory/{work_order_id}/ledger",
        response_model=ProductionOrderDetail,
        operation_id="inventory_ledger_get",
    )
    def inventory_ledger_get(
        work_order_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_inventory_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ProductionOrderDetail:
        try:
            return get_production_order(session, scope=_scope(context), work_order_id=work_order_id)
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/inventory/{work_order_id}/adjustments",
        response_model=InventoryLedgerResponse,
        status_code=201,
        operation_id="inventory_adjustment_create",
    )
    def inventory_adjustment_create(
        work_order_id: UUID,
        payload: InventoryAdjustmentCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_inventory_adjust)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> InventoryLedgerResponse:
        try:
            return adjust_inventory(
                session,
                scope=_scope(context),
                work_order_id=work_order_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    return router
