"""Shared production persistence helpers."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.organizations.scope import OrganizationScope
from app.modules.production.errors import ProductionNotFoundError, ProductionStateError
from app.modules.production.models import InventoryLedgerEntry
from app.modules.work_orders.models import WorkOrder


def locked_confirmed_order(
    session: Session, *, scope: OrganizationScope, work_order_id: UUID
) -> WorkOrder:
    row = session.scalar(
        scope.constrain(select(WorkOrder), model=WorkOrder)
        .where(WorkOrder.id == work_order_id)
        .with_for_update()
    )
    if row is None:
        raise ProductionNotFoundError
    if row.status != "confirmed":
        raise ProductionStateError
    return row


def inventory_balance(
    session: Session, *, scope: OrganizationScope, work_order_id: UUID
) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(InventoryLedgerEntry.quantity), 0)).where(
            InventoryLedgerEntry.organization_id == scope.organization_id,
            InventoryLedgerEntry.work_order_id == work_order_id,
        )
    ) or Decimal("0")
