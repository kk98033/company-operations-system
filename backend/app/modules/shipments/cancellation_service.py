"""Confirmed shipment cancellation and inventory reversal."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.models import InventoryLedgerEntry
from app.modules.shipments.common import shipment_response
from app.modules.shipments.errors import (
    ShipmentConflictError,
    ShipmentNotFoundError,
    ShipmentStateError,
)
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.shipments.schemas import ShipmentCancel, ShipmentResponse
from app.modules.work_orders.models import WorkOrder


def cancel_shipment(
    session: Session,
    *,
    scope: OrganizationScope,
    shipment_id: UUID,
    payload: ShipmentCancel,
    request_id: UUID,
) -> ShipmentResponse:
    try:
        shipment = session.scalar(
            select(Shipment)
            .where(
                Shipment.organization_id == scope.organization_id,
                Shipment.id == shipment_id,
            )
            .with_for_update()
        )
        if shipment is None:
            raise ShipmentNotFoundError
        if (
            shipment.status == "cancelled"
            and shipment.cancellation_idempotency_key == payload.idempotency_key
        ):
            return shipment_response(session, shipment)
        if shipment.status != "confirmed":
            raise ShipmentStateError
        if shipment.version != payload.expected_version:
            raise ShipmentConflictError
        items = session.scalars(
            select(ShipmentItem)
            .where(
                ShipmentItem.organization_id == scope.organization_id,
                ShipmentItem.shipment_id == shipment.id,
            )
            .order_by(ShipmentItem.work_order_id)
            .with_for_update()
        ).all()
        session.scalars(
            select(WorkOrder)
            .where(
                WorkOrder.organization_id == scope.organization_id,
                WorkOrder.id.in_([item.work_order_id for item in items]),
            )
            .order_by(WorkOrder.id)
            .with_for_update()
        ).all()
        now = datetime.now(UTC)
        for item in items:
            for event_type, quantity in (
                ("shipment_reversal_delivered", item.delivered_quantity),
                ("shipment_reversal_spare", item.spare_quantity),
            ):
                if quantity > 0:
                    session.add(
                        InventoryLedgerEntry(
                            organization_id=scope.organization_id,
                            work_order_id=item.work_order_id,
                            event_type=event_type,
                            quantity=quantity,
                            final_completion_entry_id=None,
                            inventory_adjustment_id=None,
                            shipment_item_id=item.id,
                            reason=payload.reason,
                            occurred_at=now,
                        )
                    )
        shipment.status = "cancelled"
        shipment.cancelled_at = now
        shipment.cancel_reason = payload.reason
        shipment.cancellation_idempotency_key = payload.idempotency_key
        shipment.version += 1
        shipment.updated_at = now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="shipment.cancel",
            entity_type="shipment",
            entity_id=shipment.id,
            document_number=shipment.document_number,
            reason=payload.reason,
            after={"status": "cancelled", "completion_reversed": False},
        )
        session.commit()
        return shipment_response(session, shipment)
    except IntegrityError:
        session.rollback()
        raise ShipmentConflictError from None
    except Exception:
        session.rollback()
        raise
