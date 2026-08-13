"""Pricing confirmation, cancellation, reopen, and price-memory transactions."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.authorization.capabilities import has_capability
from app.modules.organizations.scope import OrganizationScope
from app.modules.pricing.common import load_document, load_sources, pricing_response
from app.modules.pricing.errors import PricingConflictError, PricingStateError
from app.modules.pricing.models import PriceHistory, PricingItem
from app.modules.pricing.schemas import (
    PricingCancel,
    PricingConfirm,
    PricingReopen,
    PricingResponse,
)


def confirm_pricing(
    session: Session,
    *,
    scope: OrganizationScope,
    pricing_id: UUID,
    payload: PricingConfirm,
    request_id: UUID,
) -> PricingResponse:
    try:
        document = load_document(session, scope=scope, pricing_id=pricing_id, lock=True)
        if (
            document.status == "confirmed"
            and document.confirmation_idempotency_key == payload.idempotency_key
        ):
            return pricing_response(session, document)
        if document.status != "draft":
            raise PricingStateError
        if document.version != payload.expected_version:
            raise PricingConflictError
        items = session.scalars(
            select(PricingItem)
            .where(
                PricingItem.organization_id == scope.organization_id,
                PricingItem.pricing_document_id == document.id,
            )
            .order_by(PricingItem.line_no)
            .with_for_update()
        ).all()
        defaults = set(payload.update_default_line_numbers)
        if not defaults.issubset({item.line_no for item in items}):
            raise PricingConflictError
        if defaults and not has_capability(
            session,
            organization_member_id=scope.organization_member_id,
            organization_id=scope.organization_id,
            capability="price_default.update",
        ):
            raise PricingConflictError
        for item in items:
            product = item.product_name or item.content
            specification_key = (item.specification or "").strip()
            make_default = item.line_no in defaults
            if make_default:
                session.execute(
                    update(PriceHistory)
                    .where(
                        PriceHistory.organization_id == scope.organization_id,
                        PriceHistory.customer_id == document.customer_id,
                        PriceHistory.product_name == product,
                        PriceHistory.specification_key == specification_key,
                        PriceHistory.is_default.is_(True),
                    )
                    .values(is_default=False)
                )
            session.add(
                PriceHistory(
                    organization_id=scope.organization_id,
                    customer_id=document.customer_id,
                    source_pricing_item_id=item.id,
                    product_name=product,
                    specification=item.specification,
                    specification_key=specification_key,
                    content=item.content,
                    unit_price=item.unit_price,
                    plate_fee=item.plate_fee,
                    die_fee=item.die_fee,
                    price_date=document.pricing_date,
                    is_default=make_default,
                )
            )
        now = datetime.now(UTC)
        document.status = "confirmed"
        document.confirmed_at = now
        document.cancelled_at = None
        document.cancel_reason = None
        document.confirmation_idempotency_key = payload.idempotency_key
        document.version += 1
        document.updated_at = now
        document.document_snapshot = {
            "document_number": document.document_number,
            "pricing_date": document.pricing_date.isoformat(),
            "customer": document.customer_snapshot,
            "items": [
                {
                    "line_no": item.line_no,
                    "type": item.item_type,
                    "content": item.content,
                    "quantity": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "plate_fee": str(item.plate_fee),
                    "die_fee": str(item.die_fee),
                    "subtotal": str(item.subtotal),
                    "source": item.source_snapshot,
                }
                for item in items
            ],
            "total_amount": str(sum(item.subtotal for item in items)),
        }
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="pricing.confirm",
            entity_type="pricing_document",
            entity_id=document.id,
            document_number=document.document_number,
            after={
                "status": "confirmed",
                "line_count": len(items),
                "default_updates": len(defaults),
            },
        )
        session.commit()
        return pricing_response(session, document)
    except IntegrityError:
        session.rollback()
        raise PricingConflictError from None
    except Exception:
        session.rollback()
        raise


def cancel_pricing(
    session: Session,
    *,
    scope: OrganizationScope,
    pricing_id: UUID,
    payload: PricingCancel,
    request_id: UUID,
) -> PricingResponse:
    try:
        document = load_document(session, scope=scope, pricing_id=pricing_id, lock=True)
        if (
            document.status == "cancelled"
            and document.cancellation_idempotency_key == payload.idempotency_key
        ):
            return pricing_response(session, document)
        if document.status != "confirmed":
            raise PricingStateError
        from app.modules.billing.models import StatementItem

        billed = session.scalar(
            select(StatementItem.id)
            .where(
                StatementItem.organization_id == scope.organization_id,
                StatementItem.source_pricing_item_id.in_(
                    select(PricingItem.id).where(
                        PricingItem.organization_id == scope.organization_id,
                        PricingItem.pricing_document_id == document.id,
                    )
                ),
                StatementItem.is_active.is_(True),
            )
            .limit(1)
        )
        if billed is not None:
            raise PricingStateError
        if document.version != payload.expected_version:
            raise PricingConflictError
        now = datetime.now(UTC)
        document.status = "cancelled"
        document.cancelled_at = now
        document.cancel_reason = payload.reason
        document.cancellation_idempotency_key = payload.idempotency_key
        document.version += 1
        document.updated_at = now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="pricing.cancel",
            entity_type="pricing_document",
            entity_id=document.id,
            document_number=document.document_number,
            reason=payload.reason,
            after={"status": "cancelled"},
        )
        session.commit()
        return pricing_response(session, document)
    except IntegrityError:
        session.rollback()
        raise PricingConflictError from None
    except Exception:
        session.rollback()
        raise


def reopen_pricing(
    session: Session,
    *,
    scope: OrganizationScope,
    pricing_id: UUID,
    payload: PricingReopen,
    request_id: UUID,
) -> PricingResponse:
    try:
        document = load_document(session, scope=scope, pricing_id=pricing_id, lock=True)
        if (
            document.status == "draft"
            and document.reopen_idempotency_key == payload.idempotency_key
        ):
            return pricing_response(session, document)
        if document.status != "cancelled":
            raise PricingStateError
        if document.version != payload.expected_version:
            raise PricingConflictError
        base_sources = set(
            session.scalars(
                select(PricingItem.source_shipment_item_id).where(
                    PricingItem.organization_id == scope.organization_id,
                    PricingItem.pricing_document_id == document.id,
                    PricingItem.item_type == "base",
                )
            ).all()
        )
        load_sources(session, scope=scope, source_ids=base_sources, lock=True)
        document.status = "draft"
        document.confirmed_at = None
        document.cancelled_at = None
        document.cancel_reason = None
        document.reopen_idempotency_key = payload.idempotency_key
        document.confirmation_idempotency_key = None
        document.cancellation_idempotency_key = None
        document.document_snapshot = None
        document.version += 1
        document.updated_at = datetime.now(UTC)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="pricing.reopen",
            entity_type="pricing_document",
            entity_id=document.id,
            document_number=document.document_number,
            after={"status": "draft"},
        )
        session.commit()
        return pricing_response(session, document)
    except IntegrityError:
        session.rollback()
        raise PricingConflictError from None
    except Exception:
        session.rollback()
        raise
