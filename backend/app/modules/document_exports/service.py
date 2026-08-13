"""Create and retrieve immutable PDF exports."""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.billing.errors import BillingNotFoundError
from app.modules.billing.query_service import get_statement
from app.modules.document_exports.models import DocumentExport
from app.modules.document_exports.renderer import render_document_pdf
from app.modules.document_exports.schemas import DocumentExportResponse, DocumentType
from app.modules.organizations.models import Organization
from app.modules.organizations.scope import OrganizationScope
from app.modules.quotations.errors import QuotationNotFoundError
from app.modules.quotations.service import get_quotation
from app.modules.shipments.errors import ShipmentNotFoundError
from app.modules.shipments.query_service import get_shipment
from app.modules.work_orders.errors import WorkOrderNotFoundError
from app.modules.work_orders.models import WorkOrderAttachment
from app.modules.work_orders.service import get_work_order

NOT_FOUND_ERRORS = (
    BillingNotFoundError,
    QuotationNotFoundError,
    ShipmentNotFoundError,
    WorkOrderNotFoundError,
)
TEMPLATES = {
    "quotation": "quotation-gmail-a4-landscape-v1",
    "work_order": "work-order-gmail-a4-portrait-9-process-v1",
    "shipment": "shipment-a4-portrait-v1",
    "statement": "statement-a4-portrait-v1",
}


class DocumentExportNotFoundError(Exception):
    pass


class DocumentExportGenerationError(Exception):
    pass


def _response(row: DocumentExport) -> DocumentExportResponse:
    return DocumentExportResponse(
        id=row.id,
        document_type=row.document_type,
        document_id=row.document_id,
        document_number=row.document_number,
        document_version=row.document_version,
        template_version=row.template_version,
        filename=row.filename,
        content_type="application/pdf",
        byte_size=row.byte_size,
        sha256=row.sha256,
        download_url=f"/api/v1/document-exports/{row.id}/content",
        created_at=row.created_at,
    )


def _load_document(session: Session, scope: OrganizationScope, kind: str, document_id: UUID):
    loaders = {
        "quotation": lambda: get_quotation(session, scope=scope, quotation_id=document_id),
        "work_order": lambda: get_work_order(session, scope=scope, work_order_id=document_id),
        "shipment": lambda: get_shipment(session, scope=scope, shipment_id=document_id),
        "statement": lambda: get_statement(session, scope, document_id),
    }
    try:
        result = loaders[kind]()
    except NOT_FOUND_ERRORS:
        raise DocumentExportNotFoundError from None
    return result


def _version(kind: str, data: dict) -> str:
    if kind == "work_order":
        source = "|".join(
            [str(data["updated_at"]), *(item["sha256"] for item in data["print_attachments"])]
        )
        return hashlib.sha256(source.encode()).hexdigest()
    if kind in {"shipment", "statement"}:
        return str(data["version"])
    return str(data["updated_at"])


def _include_work_order_attachments(
    session: Session, *, organization_id: UUID, work_order_id: UUID, data: dict
) -> None:
    rows = session.scalars(
        select(WorkOrderAttachment)
        .where(
            WorkOrderAttachment.organization_id == organization_id,
            WorkOrderAttachment.work_order_id == work_order_id,
            WorkOrderAttachment.deleted_at.is_(None),
        )
        .order_by(WorkOrderAttachment.created_at, WorkOrderAttachment.id)
    ).all()
    data["print_attachments"] = [
        {
            "filename": row.filename,
            "mime_type": row.mime_type,
            "sha256": row.sha256,
            "content": row.content,
        }
        for row in rows
    ]


def create_document_export(
    session: Session,
    *,
    scope: OrganizationScope,
    document_type: DocumentType,
    document_id: UUID,
    request_id: UUID,
) -> DocumentExportResponse:
    response = _load_document(session, scope, document_type, document_id)
    data = response.model_dump(mode="json")
    if document_type == "work_order":
        _include_work_order_attachments(
            session,
            organization_id=scope.organization_id,
            work_order_id=document_id,
            data=data,
        )
    version = _version(document_type, data)
    template = TEMPLATES[document_type]
    existing = session.scalar(
        select(DocumentExport).where(
            DocumentExport.organization_id == scope.organization_id,
            DocumentExport.document_type == document_type,
            DocumentExport.document_id == document_id,
            DocumentExport.document_version == version,
            DocumentExport.template_version == template,
        )
    )
    if existing is not None:
        return _response(existing)
    company = session.get(Organization, scope.organization_id)
    if company is None:
        raise DocumentExportNotFoundError
    company_data = {
        "name": company.name,
        "address": company.address,
        "phone": company.phone,
        "fax": company.fax,
        "email": company.email,
        "tax_identifier": company.tax_identifier,
    }
    try:
        content = render_document_pdf(document_type, data, company_data)
    except Exception:
        raise DocumentExportGenerationError from None
    safe_number = re.sub(r"[^A-Za-z0-9._-]", "-", data["document_number"])
    row = DocumentExport(
        organization_id=scope.organization_id,
        document_type=document_type,
        document_id=document_id,
        document_number=data["document_number"],
        document_version=version,
        template_version=template,
        filename=f"{safe_number}.pdf",
        content_type="application/pdf",
        byte_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
        created_by_membership_id=scope.organization_member_id,
        created_by_user_id=scope.actor_user_id,
    )
    try:
        session.add(row)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="document.pdf_export",
            entity_type=document_type,
            entity_id=document_id,
            document_number=data["document_number"],
            after={"export_id": str(row.id), "sha256": row.sha256, "byte_size": row.byte_size},
        )
        session.commit()
        session.refresh(row)
        return _response(row)
    except IntegrityError:
        session.rollback()
        duplicate = session.scalar(
            select(DocumentExport).where(
                DocumentExport.organization_id == scope.organization_id,
                DocumentExport.document_type == document_type,
                DocumentExport.document_id == document_id,
                DocumentExport.document_version == version,
                DocumentExport.template_version == template,
            )
        )
        if duplicate is None:
            raise DocumentExportGenerationError from None
        return _response(duplicate)


def get_document_export(
    session: Session, *, organization_id: UUID, export_id: UUID
) -> DocumentExport:
    row = session.scalar(
        select(DocumentExport).where(
            DocumentExport.organization_id == organization_id, DocumentExport.id == export_id
        )
    )
    if row is None:
        raise DocumentExportNotFoundError
    return row
