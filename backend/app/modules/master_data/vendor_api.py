"""Vendor master endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import KeywordParams, PageParams, build_list_response
from app.core.database.session import get_database_session
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.master_data.errors import (
    MasterConflictError,
    MasterDuplicateError,
    MasterNotFoundError,
)
from app.modules.master_data.http import master_scope, translate_master_error
from app.modules.master_data.schemas import (
    MasterFilters,
    MasterSortParams,
    MasterStatus,
    MasterStatusUpdate,
    VendorCreate,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)
from app.modules.master_data.vendors_service import (
    create_vendor,
    list_vendors,
    set_vendor_status,
    update_vendor,
)

_read = require_capability("master_data.read")
_manage = require_capability("master_data.manage")


def build_vendor_router() -> APIRouter:
    router = APIRouter(prefix="/vendors", tags=["master-data"])

    @router.get("", response_model=VendorListResponse, operation_id="vendor_list")
    def vendor_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[OrmSession, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[MasterStatus | None, Query(alias="status")] = None,
    ) -> VendorListResponse:
        items, total = list_vendors(
            session,
            scope=master_scope(context),
            page=page,
            keyword=keyword.keyword,
            status=status_filter,
        )
        response = build_list_response(
            items=items,
            total_items=total,
            page=page,
            sort=MasterSortParams(),
            filters=MasterFilters(keyword=keyword.keyword, status=status_filter),
        )
        return VendorListResponse.model_validate(response.model_dump())

    @router.post(
        "",
        response_model=VendorResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id="vendor_create",
    )
    def vendor_create(
        payload: VendorCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> VendorResponse:
        try:
            return create_vendor(
                session,
                scope=master_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except MasterDuplicateError as error:
            translate_master_error(error)

    @router.put("/{vendor_id}", response_model=VendorResponse, operation_id="vendor_update")
    def vendor_update(
        vendor_id: UUID,
        payload: VendorUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> VendorResponse:
        try:
            return update_vendor(
                session,
                scope=master_scope(context),
                vendor_id=vendor_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except (MasterNotFoundError, MasterDuplicateError, MasterConflictError) as error:
            translate_master_error(error)

    @router.put(
        "/{vendor_id}/status", response_model=VendorResponse, operation_id="vendor_status_update"
    )
    def vendor_status_update(
        vendor_id: UUID,
        payload: MasterStatusUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> VendorResponse:
        try:
            return set_vendor_status(
                session,
                scope=master_scope(context),
                vendor_id=vendor_id,
                status=payload.status,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except (MasterNotFoundError, MasterConflictError) as error:
            translate_master_error(error)

    return router
