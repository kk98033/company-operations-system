"""Billing response and balance helpers."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.billing.errors import BillingNotFoundError
from app.modules.billing.models import Receipt, ReceiptAllocation, Statement, StatementItem
from app.modules.billing.schemas import (
    ReceiptAllocationResponse,
    ReceiptResponse,
    StatementItemResponse,
    StatementResponse,
)
from app.modules.organizations.scope import OrganizationScope


def load_statement(
    session: Session, scope: OrganizationScope, statement_id: UUID, *, lock: bool = False
) -> Statement:
    query = select(Statement).where(
        Statement.organization_id == scope.organization_id, Statement.id == statement_id
    )
    if lock:
        query = query.with_for_update()
    row = session.scalar(query)
    if row is None:
        raise BillingNotFoundError
    return row


def statement_paid_amount(session: Session, organization_id: UUID, statement_id: UUID) -> Decimal:
    return Decimal(
        session.scalar(
            select(func.coalesce(func.sum(ReceiptAllocation.amount), 0)).where(
                ReceiptAllocation.organization_id == organization_id,
                ReceiptAllocation.statement_id == statement_id,
                ReceiptAllocation.is_active.is_(True),
            )
        )
        or 0
    )


def refresh_statement_status(session: Session, row: Statement) -> Decimal:
    paid = statement_paid_amount(session, row.organization_id, row.id)
    if row.status != "cancelled":
        row.status = (
            "paid" if paid == row.grand_total else "partially_paid" if paid > 0 else "issued"
        )
    return paid


def statement_response(session: Session, row: Statement) -> StatementResponse:
    items = session.scalars(
        select(StatementItem)
        .where(
            StatementItem.organization_id == row.organization_id,
            StatementItem.statement_id == row.id,
        )
        .order_by(StatementItem.line_no)
    ).all()
    paid = statement_paid_amount(session, row.organization_id, row.id)
    return StatementResponse(
        id=row.id,
        document_number=row.document_number,
        statement_date=row.statement_date,
        period_from=row.period_from,
        period_to=row.period_to,
        customer_id=row.customer_id,
        customer_name=str(row.customer_snapshot.get("name", "")),
        status=row.status,
        version=row.version,
        tax_enabled=row.tax_enabled,
        tax_rate_percent=row.tax_rate_percent,
        rounding_scope=row.rounding_scope,
        rounding_decimal_places=row.rounding_decimal_places,
        subtotal_before_rounding=row.subtotal_before_rounding,
        rounding_adjustment=row.rounding_adjustment,
        subtotal=row.subtotal,
        tax_amount=row.tax_amount,
        grand_total=row.grand_total,
        paid_amount=paid,
        outstanding_amount=row.grand_total - paid,
        notes=row.notes,
        items=[StatementItemResponse.model_validate(item, from_attributes=True) for item in items],
        issued_at=row.issued_at,
        cancelled_at=row.cancelled_at,
        cancel_reason=row.cancel_reason,
        created_at=row.created_at,
    )


def load_receipt(
    session: Session, scope: OrganizationScope, receipt_id: UUID, *, lock: bool = False
) -> Receipt:
    query = select(Receipt).where(
        Receipt.organization_id == scope.organization_id, Receipt.id == receipt_id
    )
    if lock:
        query = query.with_for_update()
    row = session.scalar(query)
    if row is None:
        raise BillingNotFoundError
    return row


def receipt_response(session: Session, row: Receipt) -> ReceiptResponse:
    allocations = session.execute(
        select(ReceiptAllocation, Statement.document_number)
        .join(
            Statement,
            (Statement.organization_id == ReceiptAllocation.organization_id)
            & (Statement.id == ReceiptAllocation.statement_id),
        )
        .where(
            ReceiptAllocation.organization_id == row.organization_id,
            ReceiptAllocation.receipt_id == row.id,
        )
        .order_by(Statement.document_number)
    ).all()
    return ReceiptResponse(
        id=row.id,
        document_number=row.document_number,
        receipt_date=row.receipt_date,
        customer_id=row.customer_id,
        customer_name=str(row.customer_snapshot.get("name", "")),
        payment_method=row.payment_method,
        reference_number=row.reference_number,
        amount=row.amount,
        status=row.status,
        allocations=[
            ReceiptAllocationResponse(
                statement_id=item.statement_id, statement_number=number, amount=item.amount
            )
            for item, number in allocations
        ],
        notes=row.notes,
        confirmed_at=row.confirmed_at,
        reversed_at=row.reversed_at,
        reversal_reason=row.reversal_reason,
    )
