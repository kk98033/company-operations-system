"""Append-only reversal of a final completion and its inventory effect."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.common import inventory_balance, locked_confirmed_order
from app.modules.production.completion_common import (
    completed_total,
    completion_response,
    find_completion_by_idempotency,
)
from app.modules.production.errors import (
    InventoryInsufficientError,
    ProductionConflictError,
    ProductionNotFoundError,
    ProductionStateError,
)
from app.modules.production.models import FinalCompletionEntry, InventoryLedgerEntry
from app.modules.production.schemas import FinalCompletionResponse, ReversalCreate


def reverse_final_completion(
    session: Session,
    *,
    scope: OrganizationScope,
    entry_id: UUID,
    payload: ReversalCreate,
    request_id: UUID,
) -> FinalCompletionResponse:
    existing = find_completion_by_idempotency(
        session, scope=scope, idempotency_key=payload.idempotency_key
    )
    if existing is not None:
        if existing.reversal_of_id != entry_id:
            raise ProductionConflictError
        order = locked_confirmed_order(session, scope=scope, work_order_id=existing.work_order_id)
        return completion_response(
            existing,
            available=inventory_balance(session, scope=scope, work_order_id=order.id),
            order_quantity=order.order_quantity,
            completed_total=completed_total(session, scope=scope, work_order_id=order.id),
        )
    try:
        original = session.scalar(
            select(FinalCompletionEntry)
            .where(
                FinalCompletionEntry.organization_id == scope.organization_id,
                FinalCompletionEntry.id == entry_id,
            )
            .with_for_update()
        )
        if original is None:
            raise ProductionNotFoundError
        if original.entry_type != "completion":
            raise ProductionStateError
        order = locked_confirmed_order(session, scope=scope, work_order_id=original.work_order_id)
        concurrent = find_completion_by_idempotency(
            session, scope=scope, idempotency_key=payload.idempotency_key
        )
        if concurrent is not None:
            if concurrent.reversal_of_id != entry_id:
                raise ProductionConflictError
            response = completion_response(
                concurrent,
                available=inventory_balance(session, scope=scope, work_order_id=order.id),
                order_quantity=order.order_quantity,
                completed_total=completed_total(session, scope=scope, work_order_id=order.id),
            )
            session.rollback()
            return response
        reversal_count = session.scalar(
            select(func.count())
            .select_from(FinalCompletionEntry)
            .where(
                FinalCompletionEntry.organization_id == scope.organization_id,
                FinalCompletionEntry.reversal_of_id == original.id,
            )
        )
        if reversal_count:
            raise ProductionConflictError
        available = inventory_balance(session, scope=scope, work_order_id=order.id)
        if available - original.quantity < 0:
            raise InventoryInsufficientError
        now = datetime.now(UTC)
        row = FinalCompletionEntry(
            organization_id=scope.organization_id,
            work_order_id=order.id,
            entry_type="reversal",
            source_type="manual",
            quantity=-original.quantity,
            transport_process_event_id=None,
            reversal_of_id=original.id,
            correlation_id=original.correlation_id,
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
                work_order_id=order.id,
                event_type="completion_reversal",
                quantity=-original.quantity,
                final_completion_entry_id=row.id,
                inventory_adjustment_id=None,
                reason=payload.reason,
                occurred_at=now,
            )
        )
        session.flush()
        available -= original.quantity
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="production.final_completion_reverse",
            entity_type="final_completion",
            entity_id=row.id,
            reason=payload.reason,
            after={"reversal_of": str(original.id), "available": str(available)},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ProductionConflictError from None
    except Exception:
        session.rollback()
        raise
    return completion_response(row, available=available, order_quantity=order.order_quantity)
