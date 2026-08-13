"""Read models for production supervision and available inventory."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, nulls_last, or_, select
from sqlalchemy.orm import Session

from app.api.contracts import PageParams
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.common import inventory_balance
from app.modules.production.completion_service import completion_response
from app.modules.production.errors import ProductionNotFoundError
from app.modules.production.inventory_service import ledger_response
from app.modules.production.models import FinalCompletionEntry, InventoryLedgerEntry, ProcessEvent
from app.modules.production.process_service import STATE_BY_EVENT, event_response
from app.modules.production.schemas import (
    PROCESS_NAME_BY_CODE,
    InventoryPosition,
    ProcessCode,
    ProcessState,
    ProcessStateResponse,
    ProductionOrderDetail,
    ProductionOrderSummary,
)
from app.modules.work_orders.models import WorkOrder
from app.modules.work_orders.schemas import PROCESS_CODES


def _states(session: Session, *, scope: OrganizationScope, work_order_id: UUID):
    events = session.scalars(
        select(ProcessEvent)
        .where(
            ProcessEvent.organization_id == scope.organization_id,
            ProcessEvent.work_order_id == work_order_id,
        )
        .order_by(ProcessEvent.process_code, ProcessEvent.sequence_no)
    ).all()
    latest = {row.process_code: row for row in events}
    return [
        ProcessStateResponse(
            code=ProcessCode(code),
            name=PROCESS_NAME_BY_CODE[code],
            state=ProcessState(
                STATE_BY_EVENT[latest[code].event_type] if code in latest else "not_started"
            ),
            latest_event=event_response(latest[code]) if code in latest else None,
        )
        for code in PROCESS_CODES
    ]


def _summary(
    session: Session, *, scope: OrganizationScope, order: WorkOrder
) -> ProductionOrderSummary:
    states = _states(session, scope=scope, work_order_id=order.id)
    return ProductionOrderSummary(
        work_order_id=order.id,
        document_number=order.document_number,
        customer_name=str(order.customer_snapshot.get("name", "")),
        product_name=order.product_name,
        order_quantity=order.order_quantity,
        delivery_date=order.delivery_date,
        process_completed_count=sum(item.state == ProcessState.COMPLETED for item in states),
        transport_state=next(item.state for item in states if item.code == ProcessCode.TRANSPORT),
        available_quantity=inventory_balance(session, scope=scope, work_order_id=order.id),
    )


def list_production_orders(
    session: Session, *, scope: OrganizationScope, page: PageParams, keyword: str | None
) -> tuple[list[ProductionOrderSummary], int]:
    statement = scope.constrain(select(WorkOrder), model=WorkOrder).where(
        WorkOrder.status == "confirmed"
    )
    if keyword:
        statement = statement.where(
            or_(
                WorkOrder.document_number.icontains(keyword, autoescape=True),
                WorkOrder.product_name.icontains(keyword, autoescape=True),
                WorkOrder.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
            )
        )
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(nulls_last(WorkOrder.delivery_date.asc()), WorkOrder.document_number)
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [_summary(session, scope=scope, order=row) for row in rows], total


def get_production_order(
    session: Session, *, scope: OrganizationScope, work_order_id: UUID
) -> ProductionOrderDetail:
    order = session.scalar(
        scope.constrain(select(WorkOrder), model=WorkOrder).where(
            WorkOrder.id == work_order_id, WorkOrder.status == "confirmed"
        )
    )
    if order is None:
        raise ProductionNotFoundError
    available = inventory_balance(session, scope=scope, work_order_id=work_order_id)
    completions = session.scalars(
        select(FinalCompletionEntry)
        .where(
            FinalCompletionEntry.organization_id == scope.organization_id,
            FinalCompletionEntry.work_order_id == work_order_id,
        )
        .order_by(FinalCompletionEntry.created_at, FinalCompletionEntry.id)
    ).all()
    completed_total = sum((row.quantity for row in completions), Decimal("0"))
    ledger = session.scalars(
        select(InventoryLedgerEntry)
        .where(
            InventoryLedgerEntry.organization_id == scope.organization_id,
            InventoryLedgerEntry.work_order_id == work_order_id,
        )
        .order_by(InventoryLedgerEntry.created_at, InventoryLedgerEntry.id)
    ).all()
    return ProductionOrderDetail(
        order=_summary(session, scope=scope, order=order),
        processes=_states(session, scope=scope, work_order_id=work_order_id),
        final_completions=[
            completion_response(
                row,
                available=available,
                order_quantity=order.order_quantity,
                completed_total=completed_total,
            )
            for row in completions
        ],
        ledger=[ledger_response(row) for row in ledger],
    )


def list_inventory(
    session: Session,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    positive_only: bool,
) -> tuple[list[InventoryPosition], int]:
    balance = func.coalesce(func.sum(InventoryLedgerEntry.quantity), 0).label("balance")
    statement = (
        select(WorkOrder, balance)
        .outerjoin(
            InventoryLedgerEntry,
            (InventoryLedgerEntry.organization_id == WorkOrder.organization_id)
            & (InventoryLedgerEntry.work_order_id == WorkOrder.id),
        )
        .where(WorkOrder.organization_id == scope.organization_id, WorkOrder.status == "confirmed")
        .group_by(WorkOrder.id)
    )
    if keyword:
        statement = statement.where(
            or_(
                WorkOrder.document_number.icontains(keyword, autoescape=True),
                WorkOrder.product_name.icontains(keyword, autoescape=True),
                WorkOrder.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
            )
        )
    if positive_only:
        statement = statement.having(balance > 0)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.execute(
        statement.order_by(WorkOrder.document_number).offset(page.offset).limit(page.page_size)
    ).all()
    return [
        InventoryPosition(
            work_order_id=order.id,
            document_number=order.document_number,
            customer_name=str(order.customer_snapshot.get("name", "")),
            product_name=order.product_name,
            order_quantity=order.order_quantity,
            available_quantity=Decimal(value),
            delivery_date=order.delivery_date,
        )
        for order, value in rows
    ], total
