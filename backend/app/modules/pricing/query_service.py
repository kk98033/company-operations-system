"""Organization-scoped pricing lists, source status, and suggestions."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.contracts import PageParams
from app.modules.organizations.scope import OrganizationScope
from app.modules.pricing.common import load_document, pricing_response
from app.modules.pricing.models import PriceHistory, PricingDocument, PricingItem
from app.modules.pricing.schemas import (
    PendingPricingItem,
    PendingPricingStatus,
    PriceSuggestion,
    PricingStatus,
    PricingSummary,
)
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.work_orders.models import WorkOrder


def list_pricing_documents(
    session: Session,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: PricingStatus | None,
) -> tuple[list[PricingSummary], int]:
    count = func.count(PricingItem.id)
    total = func.coalesce(func.sum(PricingItem.subtotal), 0)
    statement = (
        select(PricingDocument, count, total)
        .outerjoin(
            PricingItem,
            (PricingItem.organization_id == PricingDocument.organization_id)
            & (PricingItem.pricing_document_id == PricingDocument.id),
        )
        .where(PricingDocument.organization_id == scope.organization_id)
        .group_by(PricingDocument.id)
    )
    if status is not None:
        statement = statement.where(PricingDocument.status == status.value)
    if keyword:
        statement = statement.where(
            or_(
                PricingDocument.document_number.icontains(keyword, autoescape=True),
                PricingDocument.legacy_document_number.icontains(keyword, autoescape=True),
                PricingDocument.customer_snapshot["name"]
                .as_string()
                .icontains(keyword, autoescape=True),
            )
        )
    total_rows = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.execute(
        statement.order_by(
            PricingDocument.pricing_date.desc(), PricingDocument.document_number.desc()
        )
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [
        PricingSummary(
            id=row.id,
            document_number=row.document_number,
            legacy_document_number=row.legacy_document_number,
            pricing_date=row.pricing_date,
            customer_name=str(row.customer_snapshot.get("name", "")),
            status=PricingStatus(row.status),
            line_count=line_count,
            total_amount=Decimal(amount),
        )
        for row, line_count, amount in rows
    ], total_rows


def list_pending_items(
    session: Session,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: PendingPricingStatus | None,
) -> tuple[list[PendingPricingItem], int]:
    pricing_status = case(
        (PricingItem.id.is_(None), "pending"),
        (PricingDocument.status == "draft", "pricing"),
        (PricingDocument.status == "confirmed", "priced"),
        else_="cancelled",
    ).label("pricing_status")
    statement = (
        select(ShipmentItem, Shipment, WorkOrder, PricingDocument, pricing_status)
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
        .outerjoin(
            PricingItem,
            (PricingItem.organization_id == ShipmentItem.organization_id)
            & (PricingItem.source_shipment_item_id == ShipmentItem.id)
            & (PricingItem.item_type == "base"),
        )
        .outerjoin(
            PricingDocument,
            (PricingDocument.organization_id == PricingItem.organization_id)
            & (PricingDocument.id == PricingItem.pricing_document_id),
        )
        .where(
            ShipmentItem.organization_id == scope.organization_id, Shipment.status == "confirmed"
        )
    )
    if status is not None:
        statement = statement.where(pricing_status == status.value)
    if keyword:
        statement = statement.where(
            or_(
                Shipment.document_number.icontains(keyword, autoescape=True),
                ShipmentItem.work_order_document_number.icontains(keyword, autoescape=True),
                ShipmentItem.product_name.icontains(keyword, autoescape=True),
                Shipment.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
            )
        )
    total_rows = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.execute(
        statement.order_by(
            Shipment.shipment_date.desc(), Shipment.document_number.desc(), ShipmentItem.line_no
        )
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [
        PendingPricingItem(
            shipment_item_id=item.id,
            shipment_id=shipment.id,
            shipment_document_number=shipment.document_number,
            shipment_date=shipment.shipment_date,
            customer_id=shipment.customer_id,
            customer_name=str(shipment.customer_snapshot.get("name", "")),
            work_order_document_number=item.work_order_document_number,
            product_name=item.product_name,
            specification=item.specification,
            delivered_quantity=item.delivered_quantity,
            spare_quantity=item.spare_quantity,
            suggested_unit_price=order.unit_price,
            pricing_status=PendingPricingStatus(state),
            pricing_document_id=document.id if document else None,
            pricing_document_number=document.document_number if document else None,
        )
        for item, shipment, order, document, state in rows
    ], total_rows


def get_pricing_document(session: Session, *, scope: OrganizationScope, pricing_id: UUID):
    return pricing_response(session, load_document(session, scope=scope, pricing_id=pricing_id))


def list_price_suggestions(
    session: Session,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    product_name: str,
    specification: str | None,
    limit: int = 10,
) -> list[PriceSuggestion]:
    statement = select(PriceHistory).where(
        PriceHistory.organization_id == scope.organization_id,
        PriceHistory.customer_id == customer_id,
        func.lower(func.btrim(PriceHistory.product_name)) == func.lower(func.btrim(product_name)),
    )
    if specification is not None:
        statement = statement.where(PriceHistory.specification_key == specification.strip())
    rows = session.scalars(
        statement.order_by(
            PriceHistory.is_default.desc(),
            PriceHistory.price_date.desc(),
            PriceHistory.created_at.desc(),
        ).limit(limit)
    ).all()
    return [PriceSuggestion.model_validate(row, from_attributes=True) for row in rows]
