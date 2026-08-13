"""Shipment list, draft, confirmation, cancellation, and printable snapshot API."""

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
from app.modules.shipments.errors import (
    ShipmentCompletionPermissionError,
    ShipmentConflictError,
    ShipmentInventoryError,
    ShipmentNotFoundError,
    ShipmentStateError,
)
from app.modules.shipments.query_service import get_shipment, list_available_items, list_shipments
from app.modules.shipments.schemas import (
    AvailableShipmentListResponse,
    ShipmentCancel,
    ShipmentConfirm,
    ShipmentDraftCreate,
    ShipmentDraftUpdate,
    ShipmentFilters,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentSortParams,
    ShipmentStatus,
)
from app.modules.shipments.service import (
    cancel_shipment,
    confirm_shipment,
    create_shipment_draft,
    update_shipment_draft,
)

_read = require_capability("shipment.read")
_create = require_capability("shipment.create")
_confirm = require_capability("shipment.confirm")
_cancel = require_capability("shipment.cancel")
ERRORS = (
    ShipmentNotFoundError,
    ShipmentConflictError,
    ShipmentInventoryError,
    ShipmentStateError,
    ShipmentCompletionPermissionError,
)


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, ShipmentNotFoundError):
        raise ApplicationError(
            status_code=404, code="SHIPMENT_NOT_FOUND", message="找不到出貨資料"
        ) from None
    if isinstance(error, ShipmentInventoryError):
        raise ApplicationError(
            status_code=409,
            code="SHIPMENT_INVENTORY_INSUFFICIENT",
            message="可出貨量不足；可補登真實完工或調整出貨量",
        ) from None
    if isinstance(error, ShipmentCompletionPermissionError):
        raise ApplicationError(
            status_code=403,
            code="SHIPMENT_COMPLETION_PERMISSION_REQUIRED",
            message="沒有出貨中補登完工的專用權限",
        ) from None
    if isinstance(error, ShipmentStateError):
        raise ApplicationError(
            status_code=409,
            code="SHIPMENT_STATE_CONFLICT",
            message="出貨狀態或運送完成前置條件不符合",
        ) from None
    raise ApplicationError(
        status_code=409, code="SHIPMENT_UPDATE_CONFLICT", message="出貨資料已變更，請重新載入"
    ) from None


def build_shipment_router() -> APIRouter:
    router = APIRouter(prefix="/shipments", tags=["shipments"])

    @router.get("", response_model=ShipmentListResponse, operation_id="shipment_list")
    def shipment_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status: Annotated[ShipmentStatus | None, Query()] = None,
    ) -> ShipmentListResponse:
        items, total = list_shipments(
            session, scope=_scope(context), page=page, keyword=keyword.keyword, status=status
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=ShipmentSortParams(),
            filters=ShipmentFilters(keyword=keyword.keyword, status=status),
        )
        return ShipmentListResponse.model_validate(response.model_dump())

    @router.get(
        "/available-items",
        response_model=AvailableShipmentListResponse,
        operation_id="shipment_available_item_list",
    )
    def available_item_list(
        customer_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
    ) -> AvailableShipmentListResponse:
        items, total = list_available_items(
            session,
            scope=_scope(context),
            customer_id=customer_id,
            page=page,
            keyword=keyword.keyword,
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=ShipmentSortParams(),
            filters=ShipmentFilters(keyword=keyword.keyword, status=None),
        )
        return AvailableShipmentListResponse.model_validate(response.model_dump())

    @router.post(
        "", response_model=ShipmentResponse, status_code=201, operation_id="shipment_create"
    )
    def shipment_create(
        payload: ShipmentDraftCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_create)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ShipmentResponse:
        try:
            return create_shipment_draft(
                session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get("/{shipment_id}", response_model=ShipmentResponse, operation_id="shipment_get")
    def shipment_get(
        shipment_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ShipmentResponse:
        try:
            return get_shipment(session, scope=_scope(context), shipment_id=shipment_id)
        except ERRORS as error:
            _translate(error)

    @router.put("/{shipment_id}", response_model=ShipmentResponse, operation_id="shipment_update")
    def shipment_update(
        shipment_id: UUID,
        payload: ShipmentDraftUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_create)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ShipmentResponse:
        try:
            return update_shipment_draft(
                session,
                scope=_scope(context),
                shipment_id=shipment_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/{shipment_id}/confirm", response_model=ShipmentResponse, operation_id="shipment_confirm"
    )
    def shipment_confirm(
        shipment_id: UUID,
        payload: ShipmentConfirm,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_confirm)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ShipmentResponse:
        try:
            return confirm_shipment(
                session,
                scope=_scope(context),
                shipment_id=shipment_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/{shipment_id}/cancel", response_model=ShipmentResponse, operation_id="shipment_cancel"
    )
    def shipment_cancel(
        shipment_id: UUID,
        payload: ShipmentCancel,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_cancel)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> ShipmentResponse:
        try:
            return cancel_shipment(
                session,
                scope=_scope(context),
                shipment_id=shipment_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    return router
