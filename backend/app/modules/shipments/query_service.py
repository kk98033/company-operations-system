"""Organization-scoped shipment and available-item read models."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.contracts import PageParams
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.models import InventoryLedgerEntry
from app.modules.shipments.errors import ShipmentNotFoundError
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.shipments.schemas import AvailableShipmentItem, ShipmentStatus, ShipmentSummary
from app.modules.work_orders.models import WorkOrder


def list_available_items(
    session: Session,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    page: PageParams,
    keyword: str | None,
) -> tuple[list[AvailableShipmentItem], int]:
    balance = func.coalesce(func.sum(InventoryLedgerEntry.quantity), 0).label("balance")
    statement = (
        select(WorkOrder, balance)
        .outerjoin(
            InventoryLedgerEntry,
            (InventoryLedgerEntry.organization_id == WorkOrder.organization_id)
            & (InventoryLedgerEntry.work_order_id == WorkOrder.id),
        )
        .where(
            WorkOrder.organization_id == scope.organization_id,
            WorkOrder.customer_id == customer_id,
            WorkOrder.status == "confirmed",
        )
        .group_by(WorkOrder.id)
        .having(balance > 0)
    )
    if keyword:
        statement = statement.where(
            or_(
                WorkOrder.document_number.icontains(keyword, autoescape=True),
                WorkOrder.product_name.icontains(keyword, autoescape=True),
                WorkOrder.customer_order_number.icontains(keyword, autoescape=True),
            )
        )
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.execute(
        statement.order_by(WorkOrder.document_number).offset(page.offset).limit(page.page_size)
    ).all()
    return [
        AvailableShipmentItem(
            work_order_id=order.id,
            document_number=order.document_number,
            customer_id=order.customer_id,
            customer_name=str(order.customer_snapshot.get("name", "")),
            customer_order_number=order.customer_order_number,
            product_name=order.product_name,
            specification=order.specification,
            order_quantity=order.order_quantity,
            available_quantity=Decimal(value),
        )
        for order, value in rows
    ], total


def list_shipments(
    session: Session,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: ShipmentStatus | None,
) -> tuple[list[ShipmentSummary], int]:
    delivered = func.coalesce(func.sum(ShipmentItem.delivered_quantity), 0)
    spare = func.coalesce(func.sum(ShipmentItem.spare_quantity), 0)
    line_count = func.count(ShipmentItem.id)
    statement = (
        select(Shipment, line_count, delivered, spare)
        .outerjoin(
            ShipmentItem,
            (ShipmentItem.organization_id == Shipment.organization_id)
            & (ShipmentItem.shipment_id == Shipment.id),
        )
        .where(Shipment.organization_id == scope.organization_id)
        .group_by(Shipment.id)
    )
    if status is not None:
        statement = statement.where(Shipment.status == status.value)
    if keyword:
        statement = statement.where(
            or_(
                Shipment.document_number.icontains(keyword, autoescape=True),
                Shipment.legacy_document_number.icontains(keyword, autoescape=True),
                Shipment.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
            )
        )
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.execute(
        statement.order_by(Shipment.shipment_date.desc(), Shipment.document_number.desc())
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [
        ShipmentSummary(
            id=row.id,
            document_number=row.document_number,
            legacy_document_number=row.legacy_document_number,
            shipment_date=row.shipment_date,
            customer_name=str(row.customer_snapshot.get("name", "")),
            status=ShipmentStatus(row.status),
            line_count=count,
            delivered_quantity=Decimal(delivered_quantity),
            spare_quantity=Decimal(spare_quantity),
            created_at=row.created_at,
        )
        for row, count, delivered_quantity, spare_quantity in rows
    ], total


def get_shipment(session: Session, *, scope: OrganizationScope, shipment_id: UUID):
    from app.modules.shipments.common import shipment_response

    row = session.scalar(
        select(Shipment).where(
            Shipment.organization_id == scope.organization_id,
            Shipment.id == shipment_id,
        )
    )
    if row is None:
        raise ShipmentNotFoundError
    return shipment_response(session, row)
