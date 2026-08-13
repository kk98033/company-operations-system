"""Authenticated PDF generation and download endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf, require_current_session
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.capabilities import has_capability
from app.modules.document_exports.schemas import DocumentExportResponse, DocumentType
from app.modules.document_exports.service import (
    DocumentExportGenerationError,
    DocumentExportNotFoundError,
    create_document_export,
    get_document_export,
)
from app.modules.organizations.scope import OrganizationScope

CAPABILITIES = {
    "quotation": "quotations.read",
    "work_order": "work_orders.read",
    "shipment": "shipment.read",
    "statement": "statement.read",
}


def _authorize(session: Session, context: AuthenticatedSession, document_type: str) -> None:
    if not has_capability(
        session,
        organization_member_id=context.organization_member_id,
        organization_id=context.organization_id,
        capability=CAPABILITIES[document_type],
    ):
        raise ApplicationError(status_code=403, code="PERMISSION_DENIED", message="沒有匯出此文件的權限")


def build_document_export_router() -> APIRouter:
    router = APIRouter(prefix="/document-exports", tags=["document-exports"])

    @router.post(
        "/{document_type}/{document_id}",
        response_model=DocumentExportResponse,
        status_code=201,
        operation_id="document_pdf_export_create",
    )
    def create_pdf(
        document_type: DocumentType,
        document_id: UUID,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(require_current_session)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> DocumentExportResponse:
        _authorize(session, context, document_type)
        try:
            return create_document_export(
                session,
                scope=OrganizationScope(
                    organization_id=context.organization_id,
                    organization_member_id=context.organization_member_id,
                    actor_user_id=context.user_id,
                ),
                document_type=document_type,
                document_id=document_id,
                request_id=require_request_id(request),
            )
        except DocumentExportNotFoundError:
            raise ApplicationError(status_code=404, code="DOCUMENT_NOT_FOUND", message="找不到要匯出的文件") from None
        except DocumentExportGenerationError:
            raise ApplicationError(status_code=500, code="PDF_GENERATION_FAILED", message="PDF 產生失敗，請稍後重試") from None

    @router.get(
        "/{export_id}/content",
        response_class=Response,
        operation_id="document_pdf_export_download",
        responses={200: {"content": {"application/pdf": {}}}},
    )
    def download_pdf(
        export_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(require_current_session)],
        session: Annotated[Session, Depends(get_database_session)],
    ) -> Response:
        try:
            row = get_document_export(
                session, organization_id=context.organization_id, export_id=export_id
            )
        except DocumentExportNotFoundError:
            raise ApplicationError(status_code=404, code="DOCUMENT_EXPORT_NOT_FOUND", message="找不到 PDF 匯出檔") from None
        _authorize(session, context, row.document_type)
        return Response(
            content=row.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{row.filename}"',
                "Content-Length": str(row.byte_size),
                "X-Content-SHA256": row.sha256,
                "Cache-Control": "private, no-store",
            },
        )

    return router
