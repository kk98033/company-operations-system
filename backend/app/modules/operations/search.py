"""Bounded, permission-aware search across operational documents."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.billing.models import Receipt, Statement
from app.modules.customers.models import Customer
from app.modules.operations.common import OperationsContext
from app.modules.operations.schemas import SearchResponse, SearchResult
from app.modules.pricing.models import PricingDocument
from app.modules.quotations.models import Quotation
from app.modules.shipments.models import Shipment
from app.modules.work_orders.models import ProductionCase, WorkOrder


def _result(
    row, entity_type: str, number: str, customer: str, status: str, path: str
) -> SearchResult:
    return SearchResult(
        entity_type=entity_type,
        entity_id=row.id,
        primary_text=number,
        secondary_text=customer,
        status=status,
        target_path=path,
    )


def global_search(
    session: Session, *, context: OperationsContext, keyword: str, limit: int
) -> SearchResponse:
    org = context.scope.organization_id
    results: list[SearchResult] = []
    if context.can("customers.read"):
        rows = session.scalars(
            select(Customer)
            .where(
                Customer.organization_id == org,
                or_(
                    Customer.code.icontains(keyword, autoescape=True),
                    Customer.name.icontains(keyword, autoescape=True),
                    Customer.short_name.icontains(keyword, autoescape=True),
                ),
            )
            .order_by(Customer.name)
            .limit(limit)
        ).all()
        results += [
            _result(
                r,
                "customer",
                f"{r.code}｜{r.name}",
                r.contact_name or "客戶資料",
                r.status,
                f"/customers/{r.id}",
            )
            for r in rows
        ]
    specs = [
        (
            "quotations.read",
            Quotation,
            "quotation",
            Quotation.document_number,
            Quotation.legacy_document_number,
            Quotation.customer_snapshot,
            Quotation.quotation_date,
            "/quotations/{}",
        ),
        (
            "cases.read",
            ProductionCase,
            "case",
            ProductionCase.case_number,
            ProductionCase.legacy_document_number,
            ProductionCase.customer_snapshot,
            ProductionCase.case_date,
            "/cases/{}",
        ),
        (
            "work_orders.read",
            WorkOrder,
            "work_order",
            WorkOrder.document_number,
            WorkOrder.legacy_document_number,
            WorkOrder.customer_snapshot,
            WorkOrder.order_date,
            "/work-orders/{}",
        ),
        (
            "shipment.read",
            Shipment,
            "shipment",
            Shipment.document_number,
            Shipment.legacy_document_number,
            Shipment.customer_snapshot,
            Shipment.shipment_date,
            "/shipments/{}",
        ),
        (
            "pricing.read",
            PricingDocument,
            "pricing",
            PricingDocument.document_number,
            PricingDocument.legacy_document_number,
            PricingDocument.customer_snapshot,
            PricingDocument.pricing_date,
            "/pricing/{}",
        ),
        (
            "statement.read",
            Statement,
            "statement",
            Statement.document_number,
            Statement.legacy_document_number,
            Statement.customer_snapshot,
            Statement.statement_date,
            "/statements/{}",
        ),
        (
            "receipt.read",
            Receipt,
            "receipt",
            Receipt.document_number,
            Receipt.legacy_document_number,
            Receipt.customer_snapshot,
            Receipt.receipt_date,
            "/receipts",
        ),
    ]
    for capability, model, kind, number, legacy, snapshot, date_col, path in specs:
        if not context.can(capability):
            continue
        rows = session.scalars(
            select(model)
            .where(
                model.organization_id == org,
                or_(
                    number.icontains(keyword, autoescape=True),
                    legacy.icontains(keyword, autoescape=True),
                    snapshot["name"].as_string().icontains(keyword, autoescape=True),
                ),
            )
            .order_by(date_col.desc(), number.desc())
            .limit(limit)
        ).all()
        results += [
            _result(
                r,
                kind,
                r.document_number if kind != "case" else r.case_number,
                str(r.customer_snapshot.get("name", "")),
                r.status,
                path.format(r.id),
            )
            for r in rows
        ]
    truncated = len(results) > limit
    return SearchResponse(keyword=keyword, items=results[:limit], truncated=truncated)
