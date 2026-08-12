"""Paper catalogs and fixed process endpoints."""

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
from app.modules.master_data.catalog_service import (
    CatalogKind,
    create_catalog,
    list_catalog,
    list_processes,
    set_catalog_status,
    set_process_status,
    update_catalog,
)
from app.modules.master_data.errors import (
    MasterConflictError,
    MasterDuplicateError,
    MasterNotFoundError,
)
from app.modules.master_data.http import master_scope, translate_master_error
from app.modules.master_data.schemas import (
    CatalogCreate,
    CatalogListResponse,
    CatalogResponse,
    CatalogUpdate,
    MasterFilters,
    MasterSortParams,
    MasterStatus,
    MasterStatusUpdate,
    ProcessDefinitionResponse,
)

_read = require_capability("master_data.read")
_manage = require_capability("master_data.manage")


def _catalog_router(prefix: str, kind: CatalogKind, operation_prefix: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["master-data"])

    @router.get("", response_model=CatalogListResponse, operation_id=f"{operation_prefix}_list")
    def catalog_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[OrmSession, Depends(get_database_session)],
        page: Annotated[PageParams, Depends()],
        keyword: Annotated[KeywordParams, Depends()],
        status_filter: Annotated[MasterStatus | None, Query(alias="status")] = None,
    ) -> CatalogListResponse:
        items, total = list_catalog(
            session,
            scope=master_scope(context),
            kind=kind,
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
        return CatalogListResponse.model_validate(response.model_dump())

    @router.post(
        "",
        response_model=CatalogResponse,
        status_code=status.HTTP_201_CREATED,
        operation_id=f"{operation_prefix}_create",
    )
    def catalog_create(
        payload: CatalogCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CatalogResponse:
        try:
            return create_catalog(
                session,
                scope=master_scope(context),
                kind=kind,
                payload=payload,
                request_id=require_request_id(request),
            )
        except MasterDuplicateError as error:
            translate_master_error(error)

    @router.put(
        "/{item_id}", response_model=CatalogResponse, operation_id=f"{operation_prefix}_update"
    )
    def catalog_update(
        item_id: UUID,
        payload: CatalogUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CatalogResponse:
        try:
            return update_catalog(
                session,
                scope=master_scope(context),
                kind=kind,
                item_id=item_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except (MasterNotFoundError, MasterDuplicateError, MasterConflictError) as error:
            translate_master_error(error)

    @router.put(
        "/{item_id}/status",
        response_model=CatalogResponse,
        operation_id=f"{operation_prefix}_status_update",
    )
    def catalog_status_update(
        item_id: UUID,
        payload: MasterStatusUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> CatalogResponse:
        try:
            return set_catalog_status(
                session,
                scope=master_scope(context),
                kind=kind,
                item_id=item_id,
                status=payload.status,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except (MasterNotFoundError, MasterConflictError) as error:
            translate_master_error(error)

    return router


def build_catalog_router() -> APIRouter:
    router = APIRouter(prefix="/master-data")
    router.include_router(_catalog_router("/paper-types", "paper_type", "paper_type"))
    router.include_router(_catalog_router("/paper-mills", "paper_mill", "paper_mill"))

    @router.get(
        "/process-definitions",
        response_model=list[ProcessDefinitionResponse],
        operation_id="process_definition_list",
        tags=["master-data"],
    )
    def process_definition_list(
        context: Annotated[AuthenticatedSession, Depends(_read)],
        session: Annotated[OrmSession, Depends(get_database_session)],
        status_filter: Annotated[MasterStatus | None, Query(alias="status")] = None,
    ) -> list[ProcessDefinitionResponse]:
        return list_processes(session, scope=master_scope(context), status=status_filter)

    @router.put(
        "/process-definitions/{item_id}/status",
        response_model=ProcessDefinitionResponse,
        operation_id="process_definition_status_update",
        tags=["master-data"],
    )
    def process_definition_status_update(
        item_id: UUID,
        payload: MasterStatusUpdate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[OrmSession, Depends(get_database_session)],
    ) -> ProcessDefinitionResponse:
        try:
            return set_process_status(
                session,
                scope=master_scope(context),
                item_id=item_id,
                status=payload.status,
                expected_updated_at=payload.expected_updated_at,
                request_id=require_request_id(request),
            )
        except (MasterNotFoundError, MasterConflictError) as error:
            translate_master_error(error)

    return router
