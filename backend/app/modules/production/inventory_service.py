"""Inventory adjustment and immutable ledger queries."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.common import inventory_balance, locked_confirmed_order
from app.modules.production.errors import InventoryInsufficientError, ProductionConflictError
from app.modules.production.models import InventoryAdjustment, InventoryLedgerEntry
from app.modules.production.schemas import InventoryAdjustmentCreate, InventoryLedgerResponse


def ledger_response(row: InventoryLedgerEntry) -> InventoryLedgerResponse:
    return InventoryLedgerResponse.model_validate(row, from_attributes=True)


def adjust_inventory(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    payload: InventoryAdjustmentCreate,
    request_id: UUID,
) -> InventoryLedgerResponse:
    existing = session.scalar(
        select(InventoryAdjustment).where(
            InventoryAdjustment.organization_id == scope.organization_id,
            InventoryAdjustment.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        if existing.work_order_id != work_order_id or existing.quantity != payload.quantity:
            raise ProductionConflictError
        ledger = session.scalar(
            select(InventoryLedgerEntry).where(
                InventoryLedgerEntry.organization_id == scope.organization_id,
                InventoryLedgerEntry.inventory_adjustment_id == existing.id,
            )
        )
        if ledger is None:
            raise ProductionConflictError
        return ledger_response(ledger)
    try:
        locked_confirmed_order(session, scope=scope, work_order_id=work_order_id)
        concurrent = session.scalar(
            select(InventoryAdjustment).where(
                InventoryAdjustment.organization_id == scope.organization_id,
                InventoryAdjustment.idempotency_key == payload.idempotency_key,
            )
        )
        if concurrent is not None:
            if concurrent.work_order_id != work_order_id or concurrent.quantity != payload.quantity:
                raise ProductionConflictError
            concurrent_ledger = session.scalar(
                select(InventoryLedgerEntry).where(
                    InventoryLedgerEntry.organization_id == scope.organization_id,
                    InventoryLedgerEntry.inventory_adjustment_id == concurrent.id,
                )
            )
            if concurrent_ledger is None:
                raise ProductionConflictError
            response = ledger_response(concurrent_ledger)
            session.rollback()
            return response
        balance = inventory_balance(session, scope=scope, work_order_id=work_order_id)
        if balance + payload.quantity < 0:
            raise InventoryInsufficientError
        now = datetime.now(UTC)
        adjustment = InventoryAdjustment(
            organization_id=scope.organization_id,
            work_order_id=work_order_id,
            quantity=payload.quantity,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
            approved_by_membership_id=scope.organization_member_id,
            approved_by_user_id=scope.actor_user_id,
            occurred_at=now,
        )
        session.add(adjustment)
        session.flush()
        ledger = InventoryLedgerEntry(
            organization_id=scope.organization_id,
            work_order_id=work_order_id,
            event_type="manual_adjustment",
            quantity=payload.quantity,
            final_completion_entry_id=None,
            inventory_adjustment_id=adjustment.id,
            reason=payload.reason,
            occurred_at=now,
        )
        session.add(ledger)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="inventory.adjust",
            entity_type="inventory_adjustment",
            entity_id=adjustment.id,
            reason=payload.reason,
            after={"quantity": str(payload.quantity), "available": str(balance + payload.quantity)},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ProductionConflictError from None
    except Exception:
        session.rollback()
        raise
    return ledger_response(ledger)
