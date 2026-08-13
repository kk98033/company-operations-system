"""Shared shipment persistence and response helpers."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.organizations.scope import OrganizationScope
from app.modules.shipments.errors import ShipmentConflictError, ShipmentNotFoundError
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.shipments.schemas import ShipmentItemInput, ShipmentItemResponse, ShipmentResponse
from app.modules.work_orders.models import WorkOrder


def shipment_response(
    session: Session, row: Shipment, *, warnings: list[str] | None = None
) -> ShipmentResponse:
    items = session.scalars(
        select(ShipmentItem)
        .where(
            ShipmentItem.organization_id == row.organization_id,
            ShipmentItem.shipment_id == row.id,
        )
        .order_by(ShipmentItem.line_no)
    ).all()
    return ShipmentResponse(
        id=row.id,
        document_number=row.document_number,
        shipment_date=row.shipment_date,
        customer_id=row.customer_id,
        customer_name=str(row.customer_snapshot.get("name", "")),
        delivery_address=row.delivery_address_snapshot,
        notes=row.notes,
        status=row.status,
        version=row.version,
        legacy_document_number=row.legacy_document_number,
        items=[ShipmentItemResponse.model_validate(item, from_attributes=True) for item in items],
        confirmed_at=row.confirmed_at,
        cancelled_at=row.cancelled_at,
        cancel_reason=row.cancel_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
        warnings=warnings or [],
    )


def load_customer(session: Session, *, scope: OrganizationScope, customer_id: UUID) -> Customer:
    customer = session.scalar(
        select(Customer).where(
            Customer.organization_id == scope.organization_id,
            Customer.id == customer_id,
            Customer.status == "active",
        )
    )
    if customer is None:
        raise ShipmentNotFoundError
    return customer


def load_orders(
    session: Session,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    inputs: list[ShipmentItemInput],
    lock: bool = False,
) -> dict[UUID, WorkOrder]:
    ids = {item.work_order_id for item in inputs}
    if len(ids) != len(inputs):
        raise ShipmentConflictError
    statement = (
        select(WorkOrder)
        .where(
            WorkOrder.organization_id == scope.organization_id,
            WorkOrder.id.in_(ids),
            WorkOrder.customer_id == customer_id,
            WorkOrder.status == "confirmed",
        )
        .order_by(WorkOrder.id)
    )
    if lock:
        statement = statement.with_for_update()
    rows = session.scalars(statement).all()
    if len(rows) != len(ids):
        raise ShipmentNotFoundError
    return {row.id: row for row in rows}


def replace_items(
    session: Session,
    *,
    shipment: Shipment,
    orders: dict[UUID, WorkOrder],
    inputs: list[ShipmentItemInput],
) -> None:
    session.execute(
        delete(ShipmentItem).where(
            ShipmentItem.organization_id == shipment.organization_id,
            ShipmentItem.shipment_id == shipment.id,
        )
    )
    for line_no, payload in enumerate(inputs, start=1):
        order = orders[payload.work_order_id]
        session.add(
            ShipmentItem(
                organization_id=shipment.organization_id,
                shipment_id=shipment.id,
                work_order_id=order.id,
                line_no=line_no,
                work_order_document_number=order.document_number,
                customer_order_number=order.customer_order_number,
                product_name=order.product_name,
                specification=order.specification,
                delivered_quantity=payload.delivered_quantity,
                spare_quantity=payload.spare_quantity,
                inventory_consumed_quantity=payload.delivered_quantity + payload.spare_quantity,
                available_quantity_snapshot=None,
                cumulative_delivered_snapshot=None,
            )
        )
