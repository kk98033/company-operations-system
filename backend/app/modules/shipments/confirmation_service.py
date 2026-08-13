"""Atomic shipment confirmation with optional real final completion."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.authorization.capabilities import has_capability
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.common import inventory_balance
from app.modules.production.models import FinalCompletionEntry, InventoryLedgerEntry, ProcessEvent
from app.modules.shipments.common import load_orders, shipment_response
from app.modules.shipments.errors import (
    ShipmentCompletionPermissionError,
    ShipmentConflictError,
    ShipmentInventoryError,
    ShipmentNotFoundError,
    ShipmentStateError,
)
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.shipments.schemas import ShipmentConfirm, ShipmentItemInput, ShipmentResponse
from app.modules.work_orders.models import WorkOrder


def _transport_event(
    session: Session, *, organization_id: UUID, work_order_id: UUID
) -> ProcessEvent | None:
    return session.scalar(
        select(ProcessEvent)
        .where(
            ProcessEvent.organization_id == organization_id,
            ProcessEvent.work_order_id == work_order_id,
            ProcessEvent.process_code == "transport",
        )
        .order_by(ProcessEvent.sequence_no.desc())
        .limit(1)
    )


def _add_completion(
    session: Session,
    *,
    scope: OrganizationScope,
    shipment: Shipment,
    order: WorkOrder,
    quantity: Decimal,
    reason: str,
    idempotency_key: UUID,
    now: datetime,
) -> None:
    transport = _transport_event(
        session, organization_id=scope.organization_id, work_order_id=order.id
    )
    if transport is None or transport.event_type != "complete":
        raise ShipmentStateError
    completion = FinalCompletionEntry(
        organization_id=scope.organization_id,
        work_order_id=order.id,
        entry_type="completion",
        source_type="shipment_completion",
        quantity=quantity,
        transport_process_event_id=transport.id,
        reversal_of_id=None,
        correlation_id=shipment.correlation_id,
        idempotency_key=idempotency_key,
        reason=reason,
        actor_membership_id=scope.organization_member_id,
        actor_user_id=scope.actor_user_id,
        occurred_at=now,
    )
    session.add(completion)
    session.flush()
    session.add(
        InventoryLedgerEntry(
            organization_id=scope.organization_id,
            work_order_id=order.id,
            event_type="final_completion",
            quantity=quantity,
            final_completion_entry_id=completion.id,
            inventory_adjustment_id=None,
            shipment_item_id=None,
            reason=reason,
            occurred_at=now,
        )
    )
    session.flush()


def _stage_inventory_consumption(
    session: Session,
    *,
    scope: OrganizationScope,
    shipment: Shipment,
    item: ShipmentItem,
    order: WorkOrder,
    now: datetime,
) -> None:
    available = inventory_balance(session, scope=scope, work_order_id=order.id)
    if available < item.inventory_consumed_quantity:
        raise ShipmentInventoryError
    item.available_quantity_snapshot = available
    item.cumulative_delivered_snapshot = session.scalar(
        select(func.coalesce(func.sum(ShipmentItem.delivered_quantity), 0))
        .join(
            Shipment,
            (Shipment.id == ShipmentItem.shipment_id)
            & (Shipment.organization_id == ShipmentItem.organization_id),
        )
        .where(
            ShipmentItem.organization_id == scope.organization_id,
            ShipmentItem.work_order_id == order.id,
            Shipment.status == "confirmed",
        )
    ) or Decimal("0")
    for event_type, quantity in (
        ("shipment_delivered", item.delivered_quantity),
        ("shipment_spare", item.spare_quantity),
    ):
        if quantity > 0:
            session.add(
                InventoryLedgerEntry(
                    organization_id=scope.organization_id,
                    work_order_id=order.id,
                    event_type=event_type,
                    quantity=-quantity,
                    final_completion_entry_id=None,
                    inventory_adjustment_id=None,
                    shipment_item_id=item.id,
                    reason=f"出貨單 {shipment.document_number}",
                    occurred_at=now,
                )
            )
            session.flush()


def confirm_shipment(
    session: Session,
    *,
    scope: OrganizationScope,
    shipment_id: UUID,
    payload: ShipmentConfirm,
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
            shipment.status == "confirmed"
            and shipment.confirmation_idempotency_key == payload.idempotency_key
        ):
            return shipment_response(session, shipment)
        if shipment.status != "draft":
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
        inputs = [
            ShipmentItemInput(
                work_order_id=item.work_order_id,
                delivered_quantity=item.delivered_quantity,
                spare_quantity=item.spare_quantity,
            )
            for item in items
        ]
        orders = load_orders(
            session, scope=scope, customer_id=shipment.customer_id, inputs=inputs, lock=True
        )
        completion_by_order = {entry.work_order_id: entry for entry in payload.completions}
        if len(completion_by_order) != len(payload.completions) or not set(
            completion_by_order
        ).issubset(orders):
            raise ShipmentConflictError
        if completion_by_order and not has_capability(
            session,
            organization_member_id=scope.organization_member_id,
            organization_id=scope.organization_id,
            capability="shipment.complete_and_confirm",
        ):
            raise ShipmentCompletionPermissionError
        now = datetime.now(UTC)
        warnings: list[str] = []
        for item in items:
            order = orders[item.work_order_id]
            completion = completion_by_order.get(item.work_order_id)
            if completion is not None:
                _add_completion(
                    session,
                    scope=scope,
                    shipment=shipment,
                    order=order,
                    quantity=completion.quantity,
                    reason=completion.reason,
                    idempotency_key=uuid5(payload.idempotency_key, str(order.id)),
                    now=now,
                )
                total = session.scalar(
                    select(func.coalesce(func.sum(FinalCompletionEntry.quantity), 0)).where(
                        FinalCompletionEntry.organization_id == scope.organization_id,
                        FinalCompletionEntry.work_order_id == order.id,
                    )
                ) or Decimal("0")
                if total > order.order_quantity:
                    warnings.append(
                        f"{order.document_number} 累計完工量超過訂單量，已保留原因與稽核紀錄"
                    )
            _stage_inventory_consumption(
                session, scope=scope, shipment=shipment, item=item, order=order, now=now
            )
        shipment.status = "confirmed"
        shipment.confirmed_at = now
        shipment.confirmation_idempotency_key = payload.idempotency_key
        shipment.version += 1
        shipment.updated_at = now
        shipment.document_snapshot = {
            "document_number": shipment.document_number,
            "shipment_date": shipment.shipment_date.isoformat(),
            "customer": shipment.customer_snapshot,
            "items": [
                {
                    "work_order": item.work_order_document_number,
                    "product_name": item.product_name,
                    "delivered_quantity": str(item.delivered_quantity),
                    "spare_quantity": str(item.spare_quantity),
                }
                for item in items
            ],
        }
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="shipment.confirm",
            entity_type="shipment",
            entity_id=shipment.id,
            document_number=shipment.document_number,
            after={
                "status": "confirmed",
                "line_count": len(items),
                "completion_count": len(completion_by_order),
            },
        )
        session.commit()
        return shipment_response(session, shipment, warnings=warnings)
    except IntegrityError:
        session.rollback()
        raise ShipmentConflictError from None
    except Exception:
        session.rollback()
        raise
