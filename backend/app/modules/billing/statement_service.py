"""Statement creation, issue, and cancellation transactions."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.billing.calculator import calculate_statement_amounts
from app.modules.billing.common import load_statement, statement_paid_amount, statement_response
from app.modules.billing.errors import BillingConflictError, BillingStateError
from app.modules.billing.models import Statement, StatementItem
from app.modules.billing.numbering import allocate_statement_number
from app.modules.billing.schemas import (
    StatementCancel,
    StatementCommand,
    StatementCreate,
    StatementResponse,
)
from app.modules.organizations.scope import OrganizationScope
from app.modules.pricing.models import PricingDocument, PricingItem


def create_statement(
    session: Session, *, scope: OrganizationScope, payload: StatementCreate, request_id: UUID
) -> StatementResponse:
    existing = session.scalar(
        select(Statement).where(
            Statement.organization_id == scope.organization_id,
            Statement.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return statement_response(session, existing)
    ids = set(payload.pricing_item_ids)
    if len(ids) != len(payload.pricing_item_ids):
        raise BillingConflictError
    try:
        rows = session.execute(
            select(PricingItem, PricingDocument)
            .join(
                PricingDocument,
                (PricingDocument.organization_id == PricingItem.organization_id)
                & (PricingDocument.id == PricingItem.pricing_document_id),
            )
            .where(
                PricingItem.organization_id == scope.organization_id,
                PricingItem.id.in_(ids),
                PricingDocument.status == "confirmed",
                PricingDocument.pricing_date.between(payload.period_from, payload.period_to),
            )
            .order_by(PricingDocument.document_number, PricingItem.line_no)
            .with_for_update(of=PricingItem)
        ).all()
        if len(rows) != len(ids) or len({doc.customer_id for _, doc in rows}) != 1:
            raise BillingConflictError
        used = session.scalar(
            select(StatementItem.id)
            .where(
                StatementItem.organization_id == scope.organization_id,
                StatementItem.source_pricing_item_id.in_(ids),
                StatementItem.is_active.is_(True),
            )
            .limit(1)
        )
        if used is not None:
            raise BillingConflictError
        amounts = calculate_statement_amounts(
            [item.subtotal for item, _ in rows],
            tax_enabled=payload.tax_enabled,
            tax_rate_percent=payload.tax_rate_percent,
            rounding_scope=payload.rounding_scope,
            rounding_decimal_places=payload.rounding_decimal_places,
        )
        first_doc = rows[0][1]
        statement = Statement(
            organization_id=scope.organization_id,
            document_number=allocate_statement_number(
                session, scope.organization_id, payload.statement_date
            ),
            statement_date=payload.statement_date,
            period_from=payload.period_from,
            period_to=payload.period_to,
            customer_id=first_doc.customer_id,
            customer_snapshot=first_doc.customer_snapshot,
            status="draft",
            version=1,
            tax_enabled=payload.tax_enabled,
            tax_rate_percent=payload.tax_rate_percent,
            rounding_scope=payload.rounding_scope,
            rounding_decimal_places=payload.rounding_decimal_places,
            subtotal_before_rounding=amounts.subtotal_before_rounding,
            rounding_adjustment=amounts.rounding_adjustment,
            subtotal=amounts.subtotal,
            tax_amount=amounts.tax_amount,
            grand_total=amounts.grand_total,
            notes=payload.notes,
            idempotency_key=payload.idempotency_key,
            issue_idempotency_key=None,
            cancellation_idempotency_key=None,
            legacy_document_number=None,
            document_snapshot=None,
            created_by_membership_id=scope.organization_member_id,
            created_by_user_id=scope.actor_user_id,
            issued_at=None,
            cancelled_at=None,
            cancel_reason=None,
        )
        session.add(statement)
        session.flush()
        for line_no, (item, document) in enumerate(rows, start=1):
            session.add(
                StatementItem(
                    organization_id=scope.organization_id,
                    statement_id=statement.id,
                    source_pricing_item_id=item.id,
                    source_pricing_document_id=document.id,
                    line_no=line_no,
                    content=item.content,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    plate_fee=item.plate_fee,
                    die_fee=item.die_fee,
                    amount=item.subtotal,
                    source_snapshot={
                        "pricing_document_number": document.document_number,
                        "pricing_date": document.pricing_date.isoformat(),
                        "product_name": item.product_name,
                        "specification": item.specification,
                        "pricing_source": item.source_snapshot,
                    },
                    is_active=True,
                )
            )
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="statement.create",
            entity_type="statement",
            entity_id=statement.id,
            document_number=statement.document_number,
            after={
                "status": "draft",
                "grand_total": str(statement.grand_total),
                "line_count": len(rows),
            },
        )
        session.commit()
        session.refresh(statement)
        return statement_response(session, statement)
    except IntegrityError:
        session.rollback()
        raise BillingConflictError from None
    except Exception:
        session.rollback()
        raise


def issue_statement(
    session: Session,
    *,
    scope: OrganizationScope,
    statement_id: UUID,
    payload: StatementCommand,
    request_id: UUID,
) -> StatementResponse:
    try:
        row = load_statement(session, scope, statement_id, lock=True)
        if row.status == "issued" and row.issue_idempotency_key == payload.idempotency_key:
            return statement_response(session, row)
        if row.status != "draft":
            raise BillingStateError
        if row.version != payload.expected_version:
            raise BillingConflictError
        now = datetime.now(UTC)
        row.status = "issued"
        row.issued_at = now
        row.issue_idempotency_key = payload.idempotency_key
        row.version += 1
        row.updated_at = now
        detail = statement_response(session, row)
        row.document_snapshot = detail.model_dump(mode="json")
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="statement.issue",
            entity_type="statement",
            entity_id=row.id,
            document_number=row.document_number,
            after={"status": "issued", "grand_total": str(row.grand_total)},
        )
        session.commit()
        return statement_response(session, row)
    except IntegrityError:
        session.rollback()
        raise BillingConflictError from None
    except Exception:
        session.rollback()
        raise


def cancel_statement(
    session: Session,
    *,
    scope: OrganizationScope,
    statement_id: UUID,
    payload: StatementCancel,
    request_id: UUID,
) -> StatementResponse:
    try:
        row = load_statement(session, scope, statement_id, lock=True)
        if (
            row.status == "cancelled"
            and row.cancellation_idempotency_key == payload.idempotency_key
        ):
            return statement_response(session, row)
        if (
            row.status not in {"draft", "issued"}
            or row.version != payload.expected_version
            or statement_paid_amount(session, scope.organization_id, row.id) > 0
        ):
            raise BillingStateError
        now = datetime.now(UTC)
        row.status = "cancelled"
        row.cancelled_at = now
        row.cancel_reason = payload.reason
        row.cancellation_idempotency_key = payload.idempotency_key
        row.version += 1
        row.updated_at = now
        session.flush()
        session.execute(
            update(StatementItem)
            .where(
                StatementItem.organization_id == scope.organization_id,
                StatementItem.statement_id == row.id,
            )
            .values(is_active=False)
        )
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="statement.cancel",
            entity_type="statement",
            entity_id=row.id,
            document_number=row.document_number,
            reason=payload.reason,
            after={"status": "cancelled"},
        )
        session.commit()
        return statement_response(session, row)
    except IntegrityError:
        session.rollback()
        raise BillingConflictError from None
    except Exception:
        session.rollback()
        raise
