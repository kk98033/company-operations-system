"""Work-order confirmation, cloning, and void lifecycle commands."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.work_orders.errors import WorkOrderConflictError, WorkOrderNotFoundError
from app.modules.work_orders.models import ProductionCase, WorkOrder
from app.modules.work_orders.schemas import PRINT_PROCESS_CODES, WorkOrderCreate, WorkOrderResponse
from app.modules.work_orders.service import create_work_order_row, work_order_response


def confirm_work_order(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    expected_updated_at: datetime,
    request_id: UUID,
) -> WorkOrderResponse:
    try:
        row = session.scalar(
            scope.constrain(select(WorkOrder), model=WorkOrder)
            .where(WorkOrder.id == work_order_id)
            .with_for_update()
        )
        if row is None:
            raise WorkOrderNotFoundError
        if row.status != "draft" or row.updated_at != expected_updated_at:
            raise WorkOrderConflictError
        now = datetime.now(UTC)
        snapshot = work_order_response(row).model_dump(mode="json")
        snapshot["status"] = "confirmed"
        snapshot["processes"] = [
            item for item in snapshot["processes"] if item["code"] in PRINT_PROCESS_CODES
        ]
        row.status, row.confirmed_at, row.updated_at = "confirmed", now, now
        row.document_snapshot = snapshot
        row.print_metadata = {
            "layout_version": "gmail-a4-portrait-9-process-v1",
            "paper_size": "A4",
            "orientation": "portrait",
            "process_count": 9,
            "captured_at": now.isoformat(),
        }
        parent = session.get(ProductionCase, row.case_id)
        if parent is not None and parent.status == "draft":
            parent.status, parent.updated_at = "active", now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="work_order.confirm",
            entity_type="work_order",
            entity_id=row.id,
            document_number=row.document_number,
            before={"status": "draft"},
            after={"status": "confirmed"},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return work_order_response(row)


def clone_work_order(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    order_date: date,
    request_id: UUID,
) -> WorkOrderResponse:
    source = session.scalar(
        scope.constrain(select(WorkOrder), model=WorkOrder).where(WorkOrder.id == work_order_id)
    )
    if source is None:
        raise WorkOrderNotFoundError
    payload = WorkOrderCreate(
        case_id=source.case_id,
        order_date=order_date,
        delivery_date=source.delivery_date,
        customer_id=source.customer_id,
        customer_order_number=source.customer_order_number,
        product_name=source.product_name,
        order_quantity=source.order_quantity,
        specification=source.specification,
        unit_price=source.unit_price,
        plate_fee=source.plate_fee,
        die_fee=source.die_fee,
        papers=source.papers,
        print_specification=source.print_specification,
        processes=source.processes,
        notes=source.notes,
    )
    try:
        row = create_work_order_row(session, scope=scope, payload=payload)
        row.source_work_order_id = source.id
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="work_order.clone",
            entity_type="work_order",
            entity_id=row.id,
            document_number=row.document_number,
            before={"source_id": str(source.id)},
            after={"status": "draft"},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return work_order_response(row)


def void_work_order(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    expected_updated_at: datetime,
    reason: str,
    request_id: UUID,
) -> WorkOrderResponse:
    try:
        row = session.scalar(
            scope.constrain(select(WorkOrder), model=WorkOrder)
            .where(WorkOrder.id == work_order_id)
            .with_for_update()
        )
        if row is None:
            raise WorkOrderNotFoundError
        if row.status == "void" or row.updated_at != expected_updated_at:
            raise WorkOrderConflictError
        now = datetime.now(UTC)
        row.status, row.voided_at, row.void_reason, row.updated_at = "void", now, reason, now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="work_order.void",
            entity_type="work_order",
            entity_id=row.id,
            document_number=row.document_number,
            before=None,
            after={"status": "void", "reason": reason},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return work_order_response(row)
