"""Final completion transaction that creates its inventory entry atomically."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.customers.models import CustomerWorkItem
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.common import inventory_balance, locked_confirmed_order
from app.modules.production.completion_common import (
    completed_total,
    completion_response,
    find_completion_by_idempotency,
)
from app.modules.production.errors import ProductionConflictError, ProductionStateError
from app.modules.production.models import FinalCompletionEntry, InventoryLedgerEntry, ProcessEvent
from app.modules.production.schemas import FinalCompletionCreate, FinalCompletionResponse


def _refresh_customer_work_item(session: Session, *, scope: OrganizationScope, order) -> None:
    reference = str(order.id)
    row = session.scalar(
        select(CustomerWorkItem).where(
            CustomerWorkItem.organization_id == scope.organization_id,
            CustomerWorkItem.customer_id == order.customer_id,
            CustomerWorkItem.source == "work_order",
            CustomerWorkItem.source_reference == reference,
        )
    )
    if row is None:
        row = CustomerWorkItem(
            organization_id=scope.organization_id,
            customer_id=order.customer_id,
            code=order.document_number,
            name=order.product_name,
            specification=order.specification,
            unit_price=order.unit_price,
            source="work_order",
            source_reference=reference,
            status="active",
        )
        session.add(row)
    else:
        row.name = order.product_name
        row.specification = order.specification
        row.unit_price = order.unit_price
        row.updated_at = datetime.now(UTC)


def record_final_completion(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    payload: FinalCompletionCreate,
    request_id: UUID,
) -> FinalCompletionResponse:
    existing = find_completion_by_idempotency(
        session, scope=scope, idempotency_key=payload.idempotency_key
    )
    if existing is not None:
        if existing.work_order_id != work_order_id or existing.quantity != payload.quantity:
            raise ProductionConflictError
        order = locked_confirmed_order(session, scope=scope, work_order_id=work_order_id)
        return completion_response(
            existing,
            available=inventory_balance(session, scope=scope, work_order_id=work_order_id),
            order_quantity=order.order_quantity,
            completed_total=completed_total(session, scope=scope, work_order_id=work_order_id),
        )
    try:
        order = locked_confirmed_order(session, scope=scope, work_order_id=work_order_id)
        concurrent = find_completion_by_idempotency(
            session, scope=scope, idempotency_key=payload.idempotency_key
        )
        if concurrent is not None:
            if concurrent.work_order_id != work_order_id or concurrent.quantity != payload.quantity:
                raise ProductionConflictError
            response = completion_response(
                concurrent,
                available=inventory_balance(session, scope=scope, work_order_id=work_order_id),
                order_quantity=order.order_quantity,
                completed_total=completed_total(session, scope=scope, work_order_id=work_order_id),
            )
            session.rollback()
            return response
        transport = session.scalar(
            select(ProcessEvent)
            .where(
                ProcessEvent.organization_id == scope.organization_id,
                ProcessEvent.work_order_id == work_order_id,
                ProcessEvent.process_code == "transport",
            )
            .order_by(ProcessEvent.sequence_no.desc())
            .limit(1)
        )
        if transport is None or transport.event_type != "complete":
            raise ProductionStateError
        now = datetime.now(UTC)
        row = FinalCompletionEntry(
            organization_id=scope.organization_id,
            work_order_id=work_order_id,
            entry_type="completion",
            source_type="manual",
            quantity=payload.quantity,
            transport_process_event_id=transport.id,
            reversal_of_id=None,
            correlation_id=uuid4(),
            idempotency_key=payload.idempotency_key,
            reason=payload.reason,
            actor_membership_id=scope.organization_member_id,
            actor_user_id=scope.actor_user_id,
            occurred_at=now,
        )
        session.add(row)
        session.flush()
        session.add(
            InventoryLedgerEntry(
                organization_id=scope.organization_id,
                work_order_id=work_order_id,
                event_type="final_completion",
                quantity=payload.quantity,
                final_completion_entry_id=row.id,
                inventory_adjustment_id=None,
                reason=payload.reason,
                occurred_at=now,
            )
        )
        _refresh_customer_work_item(session, scope=scope, order=order)
        session.flush()
        available = inventory_balance(session, scope=scope, work_order_id=work_order_id)
        total_completed = completed_total(session, scope=scope, work_order_id=work_order_id)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="production.final_completion",
            entity_type="final_completion",
            entity_id=row.id,
            document_number=order.document_number,
            reason=payload.reason,
            after={"quantity": str(payload.quantity), "available": str(available)},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ProductionConflictError from None
    except Exception:
        session.rollback()
        raise
    return completion_response(
        row,
        available=available,
        order_quantity=order.order_quantity,
        completed_total=total_completed,
    )
