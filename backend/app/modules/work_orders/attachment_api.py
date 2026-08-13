"""Private work-order attachment HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

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
from app.modules.work_orders.attachments import (
    delete_attachment,
    get_attachment,
    list_attachments,
    upload_attachment,
)
from app.modules.work_orders.schemas import AttachmentResponse

_order_read = require_capability("work_orders.read")
_order_manage = require_capability("work_orders.manage")


def build_attachment_router() -> APIRouter:
    router = APIRouter(prefix="/work-orders", tags=["work-orders"])

    @router.get(
        "/{work_order_id}/attachments",
        response_model=list[AttachmentResponse],
        operation_id="work_order_attachment_list",
    )
    def attachment_list(
        work_order_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_order_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> list[AttachmentResponse]:
        try:
            return list_attachments(
                session, scope=organization_scope(context), work_order_id=work_order_id
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.post(
        "/{work_order_id}/attachments",
        response_model=AttachmentResponse,
        status_code=201,
        operation_id="work_order_attachment_upload",
    )
    async def attachment_upload(
        work_order_id: UUID,
        filename: str,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> AttachmentResponse:
        try:
            return upload_attachment(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                filename=filename,
                mime_type=request.headers.get("content-type", ""),
                content=await request.body(),
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.get(
        "/{work_order_id}/attachments/{attachment_id}",
        operation_id="work_order_attachment_download",
    )
    def attachment_download(
        work_order_id: UUID,
        attachment_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_order_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> Response:
        try:
            row = get_attachment(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                attachment_id=attachment_id,
            )
            return Response(
                content=row.content,
                media_type=row.mime_type,
                headers={
                    "Content-Disposition": f'inline; filename="{row.id}"',
                    "Cache-Control": "private, no-store",
                },
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    @router.delete(
        "/{work_order_id}/attachments/{attachment_id}",
        status_code=204,
        operation_id="work_order_attachment_delete",
    )
    def attachment_delete(
        work_order_id: UUID,
        attachment_id: UUID,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_order_manage)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> None:
        try:
            delete_attachment(
                session,
                scope=organization_scope(context),
                work_order_id=work_order_id,
                attachment_id=attachment_id,
                request_id=require_request_id(request),
            )
        except WORK_ORDER_DOMAIN_ERRORS as error:
            translate_work_order_error(error)

    return router
