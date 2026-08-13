"""Scoped statement, receipt, pending billing, and aging queries."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.billing.common import (
    load_receipt,
    load_statement,
    receipt_response,
    statement_paid_amount,
    statement_response,
)
from app.modules.billing.models import Receipt, Statement, StatementItem
from app.modules.billing.schemas import (
    AgingSummary,
    PendingStatementItem,
    ReceiptResponse,
    StatementSummary,
)
from app.modules.organizations.scope import OrganizationScope
from app.modules.pricing.models import PricingDocument, PricingItem


def list_pending_statement_items(
    session: Session, scope: OrganizationScope, keyword: str | None = None
) -> list[PendingStatementItem]:
    query = (
        select(PricingItem, PricingDocument)
        .join(
            PricingDocument,
            (PricingDocument.organization_id == PricingItem.organization_id)
            & (PricingDocument.id == PricingItem.pricing_document_id),
        )
        .outerjoin(
            StatementItem,
            (StatementItem.organization_id == PricingItem.organization_id)
            & (StatementItem.source_pricing_item_id == PricingItem.id)
            & StatementItem.is_active.is_(True),
        )
        .where(
            PricingItem.organization_id == scope.organization_id,
            PricingDocument.status == "confirmed",
            StatementItem.id.is_(None),
        )
    )
    if keyword:
        query = query.where(
            or_(
                PricingDocument.document_number.icontains(keyword, autoescape=True),
                PricingDocument.customer_snapshot["name"]
                .as_string()
                .icontains(keyword, autoescape=True),
                PricingItem.content.icontains(keyword, autoescape=True),
            )
        )
    rows = session.execute(
        query.order_by(
            PricingDocument.pricing_date.desc(),
            PricingDocument.document_number.desc(),
            PricingItem.line_no,
        ).limit(500)
    ).all()
    return [
        PendingStatementItem(
            pricing_item_id=item.id,
            pricing_document_id=doc.id,
            pricing_document_number=doc.document_number,
            pricing_date=doc.pricing_date,
            customer_id=doc.customer_id,
            customer_name=str(doc.customer_snapshot.get("name", "")),
            content=item.content,
            amount=item.subtotal,
        )
        for item, doc in rows
    ]


def list_statements(
    session: Session,
    scope: OrganizationScope,
    keyword: str | None = None,
    status: str | None = None,
) -> list[StatementSummary]:
    query = select(Statement).where(Statement.organization_id == scope.organization_id)
    if status:
        query = query.where(Statement.status == status)
    if keyword:
        query = query.where(
            or_(
                Statement.document_number.icontains(keyword, autoescape=True),
                Statement.legacy_document_number.icontains(keyword, autoescape=True),
                Statement.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
            )
        )
    rows = session.scalars(
        query.order_by(Statement.statement_date.desc(), Statement.document_number.desc()).limit(500)
    ).all()
    result = []
    for row in rows:
        paid = statement_paid_amount(session, scope.organization_id, row.id)
        result.append(
            StatementSummary(
                id=row.id,
                document_number=row.document_number,
                statement_date=row.statement_date,
                customer_id=row.customer_id,
                customer_name=str(row.customer_snapshot.get("name", "")),
                grand_total=row.grand_total,
                paid_amount=paid,
                outstanding_amount=row.grand_total - paid,
                status=row.status,
            )
        )
    return result


def list_receipts(
    session: Session, scope: OrganizationScope, keyword: str | None = None
) -> list[ReceiptResponse]:
    query = select(Receipt).where(Receipt.organization_id == scope.organization_id)
    if keyword:
        query = query.where(
            or_(
                Receipt.document_number.icontains(keyword, autoescape=True),
                Receipt.legacy_document_number.icontains(keyword, autoescape=True),
                Receipt.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
                Receipt.reference_number.icontains(keyword, autoescape=True),
            )
        )
    return [
        receipt_response(session, row)
        for row in session.scalars(
            query.order_by(Receipt.receipt_date.desc(), Receipt.document_number.desc()).limit(500)
        ).all()
    ]


def list_aging(session: Session, scope: OrganizationScope, as_of: date) -> list[AgingSummary]:
    rows = session.scalars(
        select(Statement)
        .where(
            Statement.organization_id == scope.organization_id,
            Statement.status.in_(("issued", "partially_paid")),
        )
        .order_by(Statement.customer_id, Statement.statement_date)
    ).all()
    buckets: dict[UUID, dict] = {}
    for row in rows:
        outstanding = row.grand_total - statement_paid_amount(
            session, scope.organization_id, row.id
        )
        if outstanding <= 0:
            continue
        bucket = buckets.setdefault(
            row.customer_id,
            {
                "customer_name": str(row.customer_snapshot.get("name", "")),
                "current_amount": Decimal("0"),
                "days_1_30": Decimal("0"),
                "days_31_60": Decimal("0"),
                "days_61_90": Decimal("0"),
                "days_over_90": Decimal("0"),
            },
        )
        days = (as_of - row.statement_date).days
        key = (
            "current_amount"
            if days <= 0
            else "days_1_30"
            if days <= 30
            else "days_31_60"
            if days <= 60
            else "days_61_90"
            if days <= 90
            else "days_over_90"
        )
        bucket[key] += outstanding
    return [
        AgingSummary(
            customer_id=customer_id,
            total_outstanding=sum(
                (
                    value[key]
                    for key in (
                        "current_amount",
                        "days_1_30",
                        "days_31_60",
                        "days_61_90",
                        "days_over_90",
                    )
                ),
                Decimal("0"),
            ),
            **value,
        )
        for customer_id, value in buckets.items()
    ]


def get_statement(session: Session, scope: OrganizationScope, statement_id: UUID):
    return statement_response(session, load_statement(session, scope, statement_id))


def get_receipt(session: Session, scope: OrganizationScope, receipt_id: UUID):
    return receipt_response(session, load_receipt(session, scope, receipt_id))
