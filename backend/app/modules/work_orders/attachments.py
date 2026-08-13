"""Private work-order image attachment commands."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.work_orders.errors import (
    AttachmentValidationError,
    WorkOrderNotFoundError,
    WorkOrderStateError,
)
from app.modules.work_orders.models import WorkOrder, WorkOrderAttachment
from app.modules.work_orders.schemas import AttachmentResponse

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


def _order(
    session: Session,
    scope: OrganizationScope,
    work_order_id: UUID,
    *,
    editable: bool = False,
) -> WorkOrder:
    row = session.scalar(
        scope.constrain(select(WorkOrder), model=WorkOrder).where(WorkOrder.id == work_order_id)
    )
    if row is None:
        raise WorkOrderNotFoundError
    if editable and row.status != "draft":
        raise WorkOrderStateError
    return row


def _response(row: WorkOrderAttachment) -> AttachmentResponse:
    return AttachmentResponse.model_validate(row, from_attributes=True)


def list_attachments(
    session: Session, *, scope: OrganizationScope, work_order_id: UUID
) -> list[AttachmentResponse]:
    _order(session, scope, work_order_id, editable=True)
    rows = session.scalars(
        select(WorkOrderAttachment)
        .where(
            WorkOrderAttachment.organization_id == scope.organization_id,
            WorkOrderAttachment.work_order_id == work_order_id,
            WorkOrderAttachment.deleted_at.is_(None),
        )
        .order_by(WorkOrderAttachment.created_at)
    ).all()
    return [_response(row) for row in rows]


def upload_attachment(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    filename: str,
    mime_type: str,
    content: bytes,
    request_id: UUID,
) -> AttachmentResponse:
    _order(session, scope, work_order_id)
    safe_name = filename.strip().replace("/", "_").replace("\\", "_")
    if not safe_name or len(safe_name) > 255:
        raise AttachmentValidationError
    if mime_type not in ALLOWED_MIME_TYPES or not (0 < len(content) <= MAX_ATTACHMENT_BYTES):
        raise AttachmentValidationError
    row = WorkOrderAttachment(
        organization_id=scope.organization_id,
        work_order_id=work_order_id,
        filename=safe_name,
        mime_type=mime_type,
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
        content=content,
    )
    session.add(row)
    session.flush()
    record_user_audit_event(
        session,
        scope=scope,
        request_id=request_id,
        action="work_order.attachment.upload",
        entity_type="work_order_attachment",
        entity_id=row.id,
        document_number=None,
        before=None,
        after={
            "work_order_id": str(work_order_id),
            "mime_type": mime_type,
            "size_bytes": len(content),
        },
    )
    session.commit()
    return _response(row)


def get_attachment(
    session: Session, *, scope: OrganizationScope, work_order_id: UUID, attachment_id: UUID
) -> WorkOrderAttachment:
    row = session.scalar(
        select(WorkOrderAttachment).where(
            WorkOrderAttachment.organization_id == scope.organization_id,
            WorkOrderAttachment.work_order_id == work_order_id,
            WorkOrderAttachment.id == attachment_id,
            WorkOrderAttachment.deleted_at.is_(None),
        )
    )
    if row is None:
        raise WorkOrderNotFoundError
    return row


def delete_attachment(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    attachment_id: UUID,
    request_id: UUID,
) -> None:
    _order(session, scope, work_order_id, editable=True)
    row = get_attachment(
        session, scope=scope, work_order_id=work_order_id, attachment_id=attachment_id
    )
    row.deleted_at = datetime.now(UTC)
    record_user_audit_event(
        session,
        scope=scope,
        request_id=request_id,
        action="work_order.attachment.delete",
        entity_type="work_order_attachment",
        entity_id=row.id,
        document_number=None,
        before={"work_order_id": str(work_order_id)},
        after={"deleted": True},
    )
    session.commit()
