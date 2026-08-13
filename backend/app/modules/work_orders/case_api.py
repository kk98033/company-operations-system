"""Production-case HTTP endpoints."""

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
from app.modules.work_orders.case_service import (
    create_case,
    get_case,
    list_cases,
    update_case,
    void_case,
)
from app.modules.work_orders.conversion import convert_quotation
from app.modules.work_orders.schemas import (
    CaseCreate,
    CaseFilters,
    CaseListResponse,
    CaseResponse,
    CaseSortParams,
    CaseStatus,
    CaseUpdate,
    QuotationConversionRequest,
    VoidRequest,
)

_case_read = require_capability("cases.read")
_case_manage = require_capability("cases.manage")


def build_case_router() -> APIRouter:
    router = APIRouter(prefix="/cases", tags=["cases"])

    @router.get("", response_model=CaseListResponse, operation_id="case_list")
    def case_list(
        context: Annotated[AuthenticatedSession, Depends(_case_read)],
        session: Annotated[Session, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[CaseStatus | None, Query(alias="status")] = None,
    ) -> CaseListResponse:
        items, total = list_cases(
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
            sort=CaseSortParams(),
            filters=CaseFilters(keyword=keyword.keyword, status=status_filter),
        )
        return CaseListResponse.model_validate(response.model_dump())

    @router.get("/{case_id}", response_model=CaseResponse, operation_id="case_get")
    def case_get(
        case_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_case_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> CaseResponse:
        try:
            return get_case(session, scope=organization_scope(context), case_id=case_id)
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post("", response_model=CaseResponse, status_code=201, operation_id="case_create")
    def case_create(
        payload: CaseCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_case_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> CaseResponse:
        try:
            return create_case(
                session,
                scope=organization_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.put("/{case_id}", response_model=CaseResponse, operation_id="case_update")
    def case_update(
        case_id: UUID,
        payload: CaseUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_case_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> CaseResponse:
        try:
            return update_case(
                session,
                scope=organization_scope(context),
                case_id=case_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post("/{case_id}/void", response_model=CaseResponse, operation_id="case_void")
    def case_void(
        case_id: UUID,
        payload: VoidRequest,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_case_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> CaseResponse:
        try:
            return void_case(
                session,
                scope=organization_scope(context),
                case_id=case_id,
                expected_updated_at=payload.expected_updated_at,
                reason=payload.reason,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post(
        "/from-quotation/convert",
        response_model=CaseResponse,
        status_code=201,
        operation_id="case_from_quotation",
    )
    def case_from_quotation(
        payload: QuotationConversionRequest,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_case_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> CaseResponse:
        try:
            return convert_quotation(
                session,
                scope=organization_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    return router
