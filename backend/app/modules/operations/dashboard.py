"""Permission-aware operational dashboard aggregates."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.billing.models import ReceiptAllocation, Statement
from app.modules.operations.common import OperationsContext
from app.modules.operations.schemas import DashboardCard, DashboardResponse
from app.modules.pricing.models import PricingItem
from app.modules.production.models import FinalCompletionEntry, InventoryLedgerEntry
from app.modules.shipments.models import Shipment, ShipmentItem
from app.modules.work_orders.models import WorkOrder


def _count(session: Session, statement) -> int:
    return int(session.scalar(statement) or 0)


def load_dashboard(
    session: Session, *, context: OperationsContext, as_of: date
) -> DashboardResponse:
    org = context.scope.organization_id
    cards: list[DashboardCard] = []
    if context.can("work_orders.read"):
        delivered = (
            select(
                ShipmentItem.work_order_id,
                func.coalesce(func.sum(ShipmentItem.delivered_quantity), 0).label("quantity"),
            )
            .join(
                Shipment,
                (Shipment.id == ShipmentItem.shipment_id)
                & (Shipment.organization_id == ShipmentItem.organization_id),
            )
            .where(ShipmentItem.organization_id == org, Shipment.status == "confirmed")
            .group_by(ShipmentItem.work_order_id)
            .subquery()
        )
        due = _count(
            session,
            select(func.count(WorkOrder.id))
            .outerjoin(delivered, delivered.c.work_order_id == WorkOrder.id)
            .where(
                WorkOrder.organization_id == org,
                WorkOrder.status == "confirmed",
                WorkOrder.delivery_date.is_not(None),
                WorkOrder.delivery_date <= as_of,
                func.coalesce(delivered.c.quantity, 0) < WorkOrder.order_quantity,
            ),
        )
        cards.append(
            DashboardCard(
                key="due_work_orders",
                label="待交且已到交期",
                value=due,
                unit="張",
                target_path="/work-orders",
                tone="danger" if due else "success",
            )
        )
    if context.can("production.read"):
        completed = (
            select(
                FinalCompletionEntry.work_order_id,
                func.coalesce(func.sum(FinalCompletionEntry.quantity), 0).label("quantity"),
            )
            .where(FinalCompletionEntry.organization_id == org)
            .group_by(FinalCompletionEntry.work_order_id)
            .subquery()
        )
        active = _count(
            session,
            select(func.count(WorkOrder.id))
            .outerjoin(completed, completed.c.work_order_id == WorkOrder.id)
            .where(
                WorkOrder.organization_id == org,
                WorkOrder.status == "confirmed",
                func.coalesce(completed.c.quantity, 0) < WorkOrder.order_quantity,
            ),
        )
        cards.append(
            DashboardCard(
                key="production",
                label="生產中工單",
                value=active,
                unit="張",
                target_path="/production",
                tone="warning" if active else "success",
            )
        )
    if context.can("inventory.read"):
        balances = (
            select(InventoryLedgerEntry.work_order_id)
            .where(InventoryLedgerEntry.organization_id == org)
            .group_by(InventoryLedgerEntry.work_order_id)
            .having(func.sum(InventoryLedgerEntry.quantity) > 0)
            .subquery()
        )
        ready = _count(session, select(func.count()).select_from(balances))
        cards.append(
            DashboardCard(
                key="ready_to_ship",
                label="待出貨品項",
                value=ready,
                unit="筆",
                target_path="/inventory",
                tone="warning" if ready else "success",
            )
        )
    if context.can("pricing.read"):
        pending = _count(
            session,
            select(func.count(ShipmentItem.id))
            .join(
                Shipment,
                (Shipment.id == ShipmentItem.shipment_id)
                & (Shipment.organization_id == ShipmentItem.organization_id),
            )
            .outerjoin(
                PricingItem,
                (PricingItem.organization_id == ShipmentItem.organization_id)
                & (PricingItem.source_shipment_item_id == ShipmentItem.id)
                & (PricingItem.item_type == "base"),
            )
            .where(
                ShipmentItem.organization_id == org,
                Shipment.status == "confirmed",
                PricingItem.id.is_(None),
            ),
        )
        cards.append(
            DashboardCard(
                key="pending_pricing",
                label="待計價明細",
                value=pending,
                unit="筆",
                target_path="/pricing",
                tone="warning" if pending else "success",
            )
        )
    if context.can("statement.read"):
        allocated = (
            select(
                ReceiptAllocation.statement_id,
                func.coalesce(func.sum(ReceiptAllocation.amount), 0).label("paid"),
            )
            .where(ReceiptAllocation.organization_id == org, ReceiptAllocation.is_active.is_(True))
            .group_by(ReceiptAllocation.statement_id)
            .subquery()
        )
        outstanding = session.scalar(
            select(
                func.coalesce(
                    func.sum(Statement.grand_total - func.coalesce(allocated.c.paid, 0)), 0
                )
            )
            .outerjoin(allocated, allocated.c.statement_id == Statement.id)
            .where(
                Statement.organization_id == org, Statement.status.in_(("issued", "partially_paid"))
            )
        ) or Decimal("0")
        cards.append(
            DashboardCard(
                key="outstanding",
                label="未收帳款",
                value=Decimal(outstanding),
                unit="元",
                target_path="/receipts",
                tone="danger" if outstanding else "success",
            )
        )
    return DashboardResponse(as_of=as_of, cards=cards)
