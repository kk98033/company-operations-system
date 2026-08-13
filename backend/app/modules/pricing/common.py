"""Shared pricing source validation and response helpers."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.scope import OrganizationScope
from app.modules.pricing.errors import PricingConflictError, PricingNotFoundError
from app.modules.pricing.models import PricingDocument, PricingItem
from app.modules.pricing.schemas import PricingItemResponse, PricingResponse
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.work_orders.models import WorkOrder

SourceRow = tuple[ShipmentItem, Shipment, WorkOrder]


def pricing_response(session: Session, row: PricingDocument) -> PricingResponse:
    items = session.scalars(
        select(PricingItem)
        .where(
            PricingItem.organization_id == row.organization_id,
            PricingItem.pricing_document_id == row.id,
        )
        .order_by(PricingItem.line_no)
    ).all()
    return PricingResponse(
        id=row.id,
        document_number=row.document_number,
        pricing_date=row.pricing_date,
        customer_id=row.customer_id,
        customer_name=str(row.customer_snapshot.get("name", "")),
        notes=row.notes,
        status=row.status,
        version=row.version,
        legacy_document_number=row.legacy_document_number,
        items=[PricingItemResponse.model_validate(item, from_attributes=True) for item in items],
        total_amount=sum((item.subtotal for item in items), Decimal("0")),
        confirmed_at=row.confirmed_at,
        cancelled_at=row.cancelled_at,
        cancel_reason=row.cancel_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def load_document(
    session: Session, *, scope: OrganizationScope, pricing_id: UUID, lock: bool = False
) -> PricingDocument:
    statement = select(PricingDocument).where(
        PricingDocument.organization_id == scope.organization_id,
        PricingDocument.id == pricing_id,
    )
    if lock:
        statement = statement.with_for_update()
    row = session.scalar(statement)
    if row is None:
        raise PricingNotFoundError
    return row


def load_sources(
    session: Session, *, scope: OrganizationScope, source_ids: set[UUID], lock: bool = False
) -> dict[UUID, SourceRow]:
    statement = (
        select(ShipmentItem, Shipment, WorkOrder)
        .join(
            Shipment,
            (Shipment.id == ShipmentItem.shipment_id)
            & (Shipment.organization_id == ShipmentItem.organization_id),
        )
        .join(
            WorkOrder,
            (WorkOrder.id == ShipmentItem.work_order_id)
            & (WorkOrder.organization_id == ShipmentItem.organization_id),
        )
        .where(
            ShipmentItem.organization_id == scope.organization_id,
            ShipmentItem.id.in_(source_ids),
            Shipment.status == "confirmed",
        )
        .order_by(ShipmentItem.id)
    )
    if lock:
        statement = statement.with_for_update(of=ShipmentItem)
    rows = session.execute(statement).all()
    if len(rows) != len(source_ids):
        raise PricingNotFoundError
    result = {item.id: (item, shipment, order) for item, shipment, order in rows}
    if len(result) != len(source_ids):
        raise PricingConflictError
    return result
