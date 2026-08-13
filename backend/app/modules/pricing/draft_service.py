"""Create and edit pricing drafts while preserving shipment lineage."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.pricing.common import load_document, load_sources, pricing_response
from app.modules.pricing.errors import PricingConflictError, PricingStateError
from app.modules.pricing.models import PricingDocument, PricingItem
from app.modules.pricing.numbering import allocate_pricing_number
from app.modules.pricing.schemas import (
    PricingDraftCreate,
    PricingDraftUpdate,
    PricingItemInput,
    PricingItemType,
    PricingResponse,
)


def _add_item(
    session: Session,
    *,
    document: PricingDocument,
    line_no: int,
    payload: PricingItemInput,
    sources: dict,
) -> None:
    source = sources.get(payload.source_shipment_item_id)
    if payload.item_type == PricingItemType.MANUAL:
        product_name = payload.product_name or payload.content
        specification = payload.specification
        snapshot = None
    else:
        item, shipment, order = source
        if shipment.customer_id != document.customer_id:
            raise PricingConflictError
        if payload.item_type == PricingItemType.BASE and payload.quantity > item.delivered_quantity:
            raise PricingConflictError
        if payload.item_type == PricingItemType.SPARE and payload.quantity > item.spare_quantity:
            raise PricingConflictError
        product_name = payload.product_name or item.product_name
        specification = (
            payload.specification if payload.specification is not None else item.specification
        )
        snapshot = {
            "shipment_id": str(shipment.id),
            "shipment_number": shipment.document_number,
            "work_order_id": str(order.id),
            "work_order_number": order.document_number,
            "delivered_quantity": str(item.delivered_quantity),
            "spare_quantity": str(item.spare_quantity),
        }
    subtotal = payload.quantity * payload.unit_price + payload.plate_fee + payload.die_fee
    session.add(
        PricingItem(
            organization_id=document.organization_id,
            pricing_document_id=document.id,
            source_shipment_item_id=payload.source_shipment_item_id,
            line_no=line_no,
            item_type=payload.item_type.value,
            content=payload.content,
            product_name=product_name,
            specification=specification,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            plate_fee=payload.plate_fee,
            die_fee=payload.die_fee,
            subtotal=subtotal,
            source_snapshot=snapshot,
        )
    )


def _validate_items(payloads: list[PricingItemInput], expected_base: set[UUID]) -> set[UUID]:
    base_ids = [
        item.source_shipment_item_id for item in payloads if item.item_type == PricingItemType.BASE
    ]
    spare_ids = [
        item.source_shipment_item_id for item in payloads if item.item_type == PricingItemType.SPARE
    ]
    if None in base_ids or len(base_ids) != len(set(base_ids)) or set(base_ids) != expected_base:
        raise PricingConflictError
    if (
        None in spare_ids
        or len(spare_ids) != len(set(spare_ids))
        or not set(spare_ids).issubset(expected_base)
    ):
        raise PricingConflictError
    return {item.source_shipment_item_id for item in payloads if item.source_shipment_item_id}


def create_pricing_draft(
    session: Session,
    *,
    scope: OrganizationScope,
    payload: PricingDraftCreate,
    request_id: UUID,
) -> PricingResponse:
    existing = session.scalar(
        select(PricingDocument).where(
            PricingDocument.organization_id == scope.organization_id,
            PricingDocument.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return pricing_response(session, existing)
    source_ids = set(payload.shipment_item_ids)
    if len(source_ids) != len(payload.shipment_item_ids):
        raise PricingConflictError
    try:
        sources = load_sources(session, scope=scope, source_ids=source_ids, lock=True)
        customer_ids = {shipment.customer_id for _, shipment, _ in sources.values()}
        if len(customer_ids) != 1:
            raise PricingConflictError
        customer_id = customer_ids.pop()
        first_shipment = next(iter(sources.values()))[1]
        document = PricingDocument(
            organization_id=scope.organization_id,
            document_number=allocate_pricing_number(
                session, organization_id=scope.organization_id, pricing_date=payload.pricing_date
            ),
            pricing_date=payload.pricing_date,
            customer_id=customer_id,
            customer_snapshot=first_shipment.customer_snapshot,
            notes=payload.notes,
            status="draft",
            version=1,
            idempotency_key=payload.idempotency_key,
            confirmation_idempotency_key=None,
            cancellation_idempotency_key=None,
            reopen_idempotency_key=None,
            legacy_document_number=None,
            legacy_source_table=None,
            legacy_source_key=None,
            document_snapshot=None,
            created_by_membership_id=scope.organization_member_id,
            created_by_user_id=scope.actor_user_id,
            confirmed_at=None,
            cancelled_at=None,
            cancel_reason=None,
        )
        session.add(document)
        session.flush()
        for line_no, source_id in enumerate(payload.shipment_item_ids, start=1):
            item, _, order = sources[source_id]
            _add_item(
                session,
                document=document,
                line_no=line_no,
                sources=sources,
                payload=PricingItemInput(
                    source_shipment_item_id=source_id,
                    item_type=PricingItemType.BASE,
                    content=item.product_name,
                    product_name=item.product_name,
                    specification=item.specification,
                    quantity=item.delivered_quantity,
                    unit_price=order.unit_price,
                    plate_fee=Decimal("0"),
                    die_fee=Decimal("0"),
                ),
            )
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="pricing.create",
            entity_type="pricing_document",
            entity_id=document.id,
            document_number=document.document_number,
            after={"status": "draft", "base_line_count": len(source_ids)},
        )
        session.commit()
        session.refresh(document)
        return pricing_response(session, document)
    except IntegrityError:
        session.rollback()
        raise PricingConflictError from None
    except Exception:
        session.rollback()
        raise


def update_pricing_draft(
    session: Session,
    *,
    scope: OrganizationScope,
    pricing_id: UUID,
    payload: PricingDraftUpdate,
    request_id: UUID,
) -> PricingResponse:
    try:
        document = load_document(session, scope=scope, pricing_id=pricing_id, lock=True)
        if document.status != "draft":
            raise PricingStateError
        if document.version != payload.expected_version:
            raise PricingConflictError
        existing_base = set(
            session.scalars(
                select(PricingItem.source_shipment_item_id).where(
                    PricingItem.organization_id == scope.organization_id,
                    PricingItem.pricing_document_id == document.id,
                    PricingItem.item_type == "base",
                )
            ).all()
        )
        source_ids = _validate_items(payload.items, existing_base)
        sources = load_sources(session, scope=scope, source_ids=source_ids, lock=True)
        session.execute(
            delete(PricingItem).where(
                PricingItem.organization_id == scope.organization_id,
                PricingItem.pricing_document_id == document.id,
            )
        )
        session.flush()
        for line_no, item in enumerate(payload.items, start=1):
            _add_item(session, document=document, line_no=line_no, payload=item, sources=sources)
        document.pricing_date = payload.pricing_date
        document.notes = payload.notes
        document.version += 1
        document.updated_at = datetime.now(UTC)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="pricing.update",
            entity_type="pricing_document",
            entity_id=document.id,
            document_number=document.document_number,
            after={"status": "draft", "line_count": len(payload.items)},
        )
        session.commit()
        return pricing_response(session, document)
    except IntegrityError:
        session.rollback()
        raise PricingConflictError from None
    except Exception:
        session.rollback()
        raise
