"""Shipment draft create and edit transactions."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.shipments.common import (
    load_customer,
    load_orders,
    replace_items,
    shipment_response,
)
from app.modules.shipments.errors import (
    ShipmentConflictError,
    ShipmentNotFoundError,
    ShipmentStateError,
)
from app.modules.shipments.models import Shipment
from app.modules.shipments.numbering import allocate_shipment_number
from app.modules.shipments.schemas import ShipmentDraftCreate, ShipmentDraftUpdate, ShipmentResponse


def create_shipment_draft(
    session: Session, *, scope: OrganizationScope, payload: ShipmentDraftCreate, request_id: UUID
) -> ShipmentResponse:
    existing = session.scalar(
        select(Shipment).where(
            Shipment.organization_id == scope.organization_id,
            Shipment.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return shipment_response(session, existing)
    try:
        customer = load_customer(session, scope=scope, customer_id=payload.customer_id)
        orders = load_orders(session, scope=scope, customer_id=customer.id, inputs=payload.items)
        row = Shipment(
            organization_id=scope.organization_id,
            document_number=allocate_shipment_number(
                session, organization_id=scope.organization_id, shipment_date=payload.shipment_date
            ),
            shipment_date=payload.shipment_date,
            customer_id=customer.id,
            customer_snapshot={
                "code": customer.code,
                "name": customer.name,
                "address": customer.address,
            },
            delivery_address_snapshot=payload.delivery_address or customer.address,
            notes=payload.notes,
            status="draft",
            version=1,
            idempotency_key=payload.idempotency_key,
            confirmation_idempotency_key=None,
            cancellation_idempotency_key=None,
            correlation_id=uuid4(),
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
        session.add(row)
        session.flush()
        replace_items(session, shipment=row, orders=orders, inputs=payload.items)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="shipment.create",
            entity_type="shipment",
            entity_id=row.id,
            document_number=row.document_number,
            after={"status": "draft", "line_count": len(payload.items)},
        )
        session.commit()
        session.refresh(row)
        return shipment_response(session, row)
    except IntegrityError:
        session.rollback()
        raise ShipmentConflictError from None
    except Exception:
        session.rollback()
        raise


def update_shipment_draft(
    session: Session,
    *,
    scope: OrganizationScope,
    shipment_id: UUID,
    payload: ShipmentDraftUpdate,
    request_id: UUID,
) -> ShipmentResponse:
    try:
        row = session.scalar(
            select(Shipment)
            .where(
                Shipment.organization_id == scope.organization_id,
                Shipment.id == shipment_id,
            )
            .with_for_update()
        )
        if row is None:
            raise ShipmentNotFoundError
        if row.status != "draft":
            raise ShipmentStateError
        if row.version != payload.expected_version:
            raise ShipmentConflictError
        orders = load_orders(
            session, scope=scope, customer_id=row.customer_id, inputs=payload.items
        )
        row.shipment_date = payload.shipment_date
        row.delivery_address_snapshot = payload.delivery_address
        row.notes = payload.notes
        row.version += 1
        row.updated_at = datetime.now(UTC)
        replace_items(session, shipment=row, orders=orders, inputs=payload.items)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="shipment.update",
            entity_type="shipment",
            entity_id=row.id,
            document_number=row.document_number,
            after={"status": "draft", "line_count": len(payload.items)},
        )
        session.commit()
        return shipment_response(session, row)
    except IntegrityError:
        session.rollback()
        raise ShipmentConflictError from None
    except Exception:
        session.rollback()
        raise
