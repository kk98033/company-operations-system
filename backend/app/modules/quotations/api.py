"""Quotation HTTP endpoints."""

from datetime import date, datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import KeywordParams, PageParams, build_list_response
from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.organizations.scope import OrganizationScope
from app.modules.quotations.errors import (
    QuotationConflictError,
    QuotationNotFoundError,
    QuotationNumberExhaustedError,
    QuotationStateError,
)
from app.modules.quotations.schemas import (
    QuotationClone,
    QuotationCreate,
    QuotationFilters,
    QuotationListResponse,
    QuotationResponse,
    QuotationSortParams,
    QuotationStatus,
    QuotationUpdate,
    QuotationVoid,
)
from app.modules.quotations.service import (
    clone_quotation,
    confirm_quotation,
    create_quotation,
    get_quotation,
    list_quotations,
    update_quotation,
    void_quotation,
)

_read = require_capability("quotations.read")
_manage = require_capability("quotations.manage")
_confirm = require_capability("quotations.confirm")


class ConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: datetime


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, QuotationNotFoundError):
        raise ApplicationError(
            status_code=404, code="QUOTATION_NOT_FOUND", message="找不到報價資料"
        ) from None
    if isinstance(error, QuotationNumberExhaustedError):
        raise ApplicationError(
            status_code=409,
            code="QUOTATION_NUMBER_EXHAUSTED",
            message="當日報價單號已用完，請聯絡系統管理者",
        ) from None
    if isinstance(error, QuotationStateError):
        raise ApplicationError(
            status_code=409, code="QUOTATION_STATE_CONFLICT", message="目前報價狀態不允許此操作"
        ) from None
    raise ApplicationError(
        status_code=409, code="QUOTATION_UPDATE_CONFLICT", message="報價已被其他人更新，請重新載入"
    ) from None


def build_quotation_router() -> APIRouter:
    router = APIRouter(prefix="/quotations", tags=["quotations"])

    @router.get("", response_model=QuotationListResponse, operation_id="quotation_list")
    def quotation_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[OrmSession, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[QuotationStatus | None, Query(alias="status")] = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> QuotationListResponse:
        if date_from and date_to and date_from > date_to:
            raise ApplicationError(
                status_code=422, code="DATE_RANGE_INVALID", message="起日不可晚於迄日"
            )
        items, total = list_quotations(
            session,
            scope=_scope(context),
            page=page,
            keyword=keyword.keyword,
            status=status_filter,
            date_from=date_from,
            date_to=date_to,
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=QuotationSortParams(),
            filters=QuotationFilters(
                keyword=keyword.keyword, status=status_filter, date_from=date_from, date_to=date_to
            ),
        )
        return QuotationListResponse.model_validate(response.model_dump())

    @router.get("/{quotation_id}", response_model=QuotationResponse, operation_id="quotation_get")
    def quotation_get(
        quotation_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> QuotationResponse:
        try:
            return get_quotation(session, scope=_scope(context), quotation_id=quotation_id)
        except QuotationNotFoundError as error:
            _translate(error)

    @router.post(
        "",
        response_model=QuotationResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="quotation_create",
    )
    def quotation_create(
        payload: QuotationCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> QuotationResponse:
        try:
            return create_quotation(
                session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except (
            QuotationNotFoundError,
            QuotationConflictError,
            QuotationNumberExhaustedError,
        ) as error:
            _translate(error)

    @router.put(
        "/{quotation_id}", response_model=QuotationResponse, operation_id="quotation_update"
    )
    def quotation_update(
        quotation_id: UUID,
        payload: QuotationUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> QuotationResponse:
        try:
            return update_quotation(
                session,
                scope=_scope(context),
                quotation_id=quotation_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except (QuotationNotFoundError, QuotationConflictError, QuotationStateError) as error:
            _translate(error)

    @router.post(
        "/{quotation_id}/confirm",
        response_model=QuotationResponse,
        operation_id="quotation_confirm",
    )
    def quotation_confirm(
        quotation_id: UUID,
        payload: ConfirmRequest,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_confirm)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> QuotationResponse:
        try:
            return confirm_quotation(
                session,
                scope=_scope(context),
                quotation_id=quotation_id,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except (QuotationNotFoundError, QuotationConflictError, QuotationStateError) as error:
            _translate(error)

    @router.post(
        "/{quotation_id}/clone",
        response_model=QuotationResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="quotation_clone",
    )
    def quotation_clone(
        quotation_id: UUID,
        payload: QuotationClone,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> QuotationResponse:
        try:
            return clone_quotation(
                session,
                scope=_scope(context),
                quotation_id=quotation_id,
                quotation_date=payload.quotation_date,
                request_id=require_request_id(request),
            )
        except (
            QuotationNotFoundError,
            QuotationConflictError,
            QuotationNumberExhaustedError,
        ) as error:
            _translate(error)

    @router.post(
        "/{quotation_id}/void",
        response_model=QuotationResponse,
        operation_id="quotation_void",
    )
    def quotation_void(
        quotation_id: UUID,
        payload: QuotationVoid,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_confirm)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> QuotationResponse:
        try:
            return void_quotation(
                session,
                scope=_scope(context),
                quotation_id=quotation_id,
                expected_updated_at=payload.expected_updated_at,
                reason=payload.reason,
                request_id=require_request_id(request),
            )
        except (QuotationNotFoundError, QuotationConflictError, QuotationStateError) as error:
            _translate(error)

    return router
