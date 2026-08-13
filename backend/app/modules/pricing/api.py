"""Pricing lists, drafts, lifecycle, and price suggestion API."""

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
from app.modules.pricing.draft_service import create_pricing_draft, update_pricing_draft
from app.modules.pricing.errors import PricingConflictError, PricingNotFoundError, PricingStateError
from app.modules.pricing.lifecycle_service import cancel_pricing, confirm_pricing, reopen_pricing
from app.modules.pricing.query_service import (
    get_pricing_document,
    list_pending_items,
    list_price_suggestions,
    list_pricing_documents,
)
from app.modules.pricing.schemas import (
    PendingPricingFilters,
    PendingPricingListResponse,
    PendingPricingStatus,
    PriceSuggestionListResponse,
    PricingCancel,
    PricingConfirm,
    PricingDraftCreate,
    PricingDraftUpdate,
    PricingFilters,
    PricingListResponse,
    PricingReopen,
    PricingResponse,
    PricingSortParams,
    PricingStatus,
)

_read = require_capability("pricing.read")
_create = require_capability("pricing.create")
_confirm = require_capability("pricing.confirm")
_cancel = require_capability("pricing.cancel")
ERRORS = (PricingNotFoundError, PricingConflictError, PricingStateError)


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, PricingNotFoundError):
        raise ApplicationError(
            status_code=404, code="PRICING_NOT_FOUND", message="找不到計價資料"
        ) from None
    if isinstance(error, PricingStateError):
        raise ApplicationError(
            status_code=409, code="PRICING_STATE_CONFLICT", message="計價狀態不允許此操作"
        ) from None
    raise ApplicationError(
        status_code=409,
        code="PRICING_UPDATE_CONFLICT",
        message="來源已計價或資料已變更，請重新載入",
    ) from None


def build_pricing_router() -> APIRouter:
    router = APIRouter(tags=["pricing"])

    @router.get(
        "/pricing-documents", response_model=PricingListResponse, operation_id="pricing_list"
    )
    def pricing_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status: Annotated[PricingStatus | None, Query()] = None,
    ) -> PricingListResponse:
        items, total = list_pricing_documents(
            session, scope=_scope(context), page=page, keyword=keyword.keyword, status=status
        )
        result = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=PricingSortParams(),
            filters=PricingFilters(keyword=keyword.keyword, status=status),
        )
        return PricingListResponse.model_validate(result.model_dump())

    @router.get(
        "/pricing-documents/pending-items",
        response_model=PendingPricingListResponse,
        operation_id="pricing_pending_item_list",
    )
    def pending_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status: Annotated[PendingPricingStatus | None, Query()] = None,
    ) -> PendingPricingListResponse:
        items, total = list_pending_items(
            session, scope=_scope(context), page=page, keyword=keyword.keyword, status=status
        )
        result = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=PricingSortParams(),
            filters=PendingPricingFilters(keyword=keyword.keyword, status=status),
        )
        return PendingPricingListResponse.model_validate(result.model_dump())

    @router.post(
        "/pricing-documents",
        response_model=PricingResponse,
        status_code=201,
        operation_id="pricing_create",
    )
    def pricing_create(
        payload: PricingDraftCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_create)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> PricingResponse:
        try:
            return create_pricing_draft(
                session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get(
        "/pricing-documents/{pricing_id}",
        response_model=PricingResponse,
        operation_id="pricing_get",
    )
    def pricing_get(
        pricing_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> PricingResponse:
        try:
            return get_pricing_document(session, scope=_scope(context), pricing_id=pricing_id)
        except ERRORS as error:
            _translate(error)

    @router.put(
        "/pricing-documents/{pricing_id}",
        response_model=PricingResponse,
        operation_id="pricing_update",
    )
    def pricing_update(
        pricing_id: UUID,
        payload: PricingDraftUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_create)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> PricingResponse:
        try:
            return update_pricing_draft(
                session,
                scope=_scope(context),
                pricing_id=pricing_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/pricing-documents/{pricing_id}/confirm",
        response_model=PricingResponse,
        operation_id="pricing_confirm",
    )
    def pricing_confirm(
        pricing_id: UUID,
        payload: PricingConfirm,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_confirm)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> PricingResponse:
        try:
            return confirm_pricing(
                session,
                scope=_scope(context),
                pricing_id=pricing_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/pricing-documents/{pricing_id}/cancel",
        response_model=PricingResponse,
        operation_id="pricing_cancel",
    )
    def pricing_cancel(
        pricing_id: UUID,
        payload: PricingCancel,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_cancel)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> PricingResponse:
        try:
            return cancel_pricing(
                session,
                scope=_scope(context),
                pricing_id=pricing_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/pricing-documents/{pricing_id}/reopen",
        response_model=PricingResponse,
        operation_id="pricing_reopen",
    )
    def pricing_reopen(
        pricing_id: UUID,
        payload: PricingReopen,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_cancel)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> PricingResponse:
        try:
            return reopen_pricing(
                session,
                scope=_scope(context),
                pricing_id=pricing_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get(
        "/price-suggestions",
        response_model=PriceSuggestionListResponse,
        operation_id="price_suggestion_list",
    )
    def suggestion_list(
        customer_id: UUID,
        product_name: str,
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[Session, Depends(get_database_session)],
        specification: str | None = None,
    ) -> PriceSuggestionListResponse:
        return PriceSuggestionListResponse(
            items=list_price_suggestions(
                session,
                scope=_scope(context),
                customer_id=customer_id,
                product_name=product_name,
                specification=specification,
            )
        )

    return router
