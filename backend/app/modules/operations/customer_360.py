"""Customer-centric cross-module activity view."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.billing.models import Receipt, ReceiptAllocation, Statement
from app.modules.customers.models import Customer
from app.modules.operations.common import OperationsContext
from app.modules.operations.schemas import CustomerActivity, CustomerOverviewResponse
from app.modules.pricing.models import PricingDocument
from app.modules.quotations.models import Quotation
from app.modules.shipments.models import Shipment
from app.modules.work_orders.models import ProductionCase, WorkOrder


class CustomerOverviewNotFoundError(RuntimeError):
    pass


def load_customer_overview(
    session: Session, *, context: OperationsContext, customer_id: UUID
) -> CustomerOverviewResponse:
    org = context.scope.organization_id
    customer = session.scalar(
        select(Customer).where(Customer.organization_id == org, Customer.id == customer_id)
    )
    if customer is None:
        raise CustomerOverviewNotFoundError
    specs = [
        (
            "quotations.read",
            "quotation",
            Quotation,
            Quotation.quotation_date,
            Quotation.document_number,
            "/quotations/{}",
        ),
        (
            "cases.read",
            "case",
            ProductionCase,
            ProductionCase.case_date,
            ProductionCase.case_number,
            "/cases/{}",
        ),
        (
            "work_orders.read",
            "work_order",
            WorkOrder,
            WorkOrder.order_date,
            WorkOrder.document_number,
            "/work-orders/{}",
        ),
        (
            "shipment.read",
            "shipment",
            Shipment,
            Shipment.shipment_date,
            Shipment.document_number,
            "/shipments/{}",
        ),
        (
            "pricing.read",
            "pricing",
            PricingDocument,
            PricingDocument.pricing_date,
            PricingDocument.document_number,
            "/pricing/{}",
        ),
        (
            "statement.read",
            "statement",
            Statement,
            Statement.statement_date,
            Statement.document_number,
            "/statements/{}",
        ),
        (
            "receipt.read",
            "receipt",
            Receipt,
            Receipt.receipt_date,
            Receipt.document_number,
            "/receipts",
        ),
    ]
    counts: dict[str, int] = {}
    activity: list[CustomerActivity] = []
    for capability, kind, model, date_col, number_col, path in specs:
        if not context.can(capability):
            continue
        base = select(model).where(model.organization_id == org, model.customer_id == customer_id)
        counts[kind] = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        for row in session.scalars(
            base.order_by(date_col.desc(), number_col.desc()).limit(10)
        ).all():
            number = row.case_number if kind == "case" else row.document_number
            activity.append(
                CustomerActivity(
                    entity_type=kind,
                    entity_id=row.id,
                    document_number=number,
                    activity_date=getattr(row, date_col.key),
                    summary=kind,
                    status=row.status,
                    target_path=path.format(row.id),
                )
            )
    outstanding: Decimal | None = None
    if context.can("statement.read"):
        statements = session.scalars(
            select(Statement).where(
                Statement.organization_id == org,
                Statement.customer_id == customer_id,
                Statement.status.in_(("issued", "partially_paid")),
            )
        ).all()
        outstanding = sum(
            (
                r.grand_total
                - (
                    session.scalar(
                        select(func.coalesce(func.sum(ReceiptAllocation.amount), 0)).where(
                            ReceiptAllocation.organization_id == org,
                            ReceiptAllocation.statement_id == r.id,
                            ReceiptAllocation.is_active.is_(True),
                        )
                    )
                    or Decimal("0")
                )
                for r in statements
            ),
            Decimal("0"),
        )
    activity.sort(key=lambda item: (item.activity_date, item.document_number), reverse=True)
    return CustomerOverviewResponse(
        customer_id=customer.id,
        customer_code=customer.code,
        customer_name=customer.name,
        customer_status=customer.status,
        counts=counts,
        outstanding_amount=outstanding,
        recent_activity=activity[:30],
    )
