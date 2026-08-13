"""Receipt allocation and reversal ledger transactions."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.billing.common import (
    load_receipt,
    load_statement,
    receipt_response,
    refresh_statement_status,
    statement_paid_amount,
)
from app.modules.billing.errors import BillingConflictError, BillingStateError
from app.modules.billing.models import Receipt, ReceiptAllocation
from app.modules.billing.numbering import allocate_receipt_number
from app.modules.billing.schemas import ReceiptCreate, ReceiptResponse, ReceiptReverse
from app.modules.organizations.scope import OrganizationScope


def create_receipt(
    session: Session, *, scope: OrganizationScope, payload: ReceiptCreate, request_id: UUID
) -> ReceiptResponse:
    existing = session.scalar(
        select(Receipt).where(
            Receipt.organization_id == scope.organization_id,
            Receipt.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return receipt_response(session, existing)
    if len({item.statement_id for item in payload.allocations}) != len(payload.allocations):
        raise BillingConflictError
    allocated = sum((item.amount for item in payload.allocations), Decimal("0"))
    if allocated > payload.amount:
        raise BillingConflictError
    try:
        statements = [
            load_statement(session, scope, item.statement_id, lock=True)
            for item in payload.allocations
        ]
        if any(
            row.customer_id != payload.customer_id or row.status not in {"issued", "partially_paid"}
            for row in statements
        ):
            raise BillingStateError
        for allocation, statement in zip(payload.allocations, statements, strict=True):
            if allocation.amount > statement.grand_total - statement_paid_amount(
                session, scope.organization_id, statement.id
            ):
                raise BillingConflictError
        now = datetime.now(UTC)
        first = statements[0]
        receipt = Receipt(
            organization_id=scope.organization_id,
            document_number=allocate_receipt_number(
                session, scope.organization_id, payload.receipt_date
            ),
            receipt_date=payload.receipt_date,
            customer_id=payload.customer_id,
            customer_snapshot=first.customer_snapshot,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            amount=payload.amount,
            status="confirmed",
            notes=payload.notes,
            idempotency_key=payload.idempotency_key,
            reversal_idempotency_key=None,
            legacy_document_number=None,
            created_by_membership_id=scope.organization_member_id,
            created_by_user_id=scope.actor_user_id,
            confirmed_at=now,
            reversed_at=None,
            reversal_reason=None,
        )
        session.add(receipt)
        session.flush()
        for allocation in payload.allocations:
            session.add(
                ReceiptAllocation(
                    organization_id=scope.organization_id,
                    receipt_id=receipt.id,
                    statement_id=allocation.statement_id,
                    amount=allocation.amount,
                    is_active=True,
                )
            )
        session.flush()
        for statement in statements:
            refresh_statement_status(session, statement)
            statement.version += 1
            statement.updated_at = now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="receipt.record",
            entity_type="receipt",
            entity_id=receipt.id,
            document_number=receipt.document_number,
            after={
                "amount": str(receipt.amount),
                "allocated": str(allocated),
                "statement_count": len(statements),
            },
        )
        session.commit()
        return receipt_response(session, receipt)
    except IntegrityError:
        session.rollback()
        raise BillingConflictError from None
    except Exception:
        session.rollback()
        raise


def reverse_receipt(
    session: Session,
    *,
    scope: OrganizationScope,
    receipt_id: UUID,
    payload: ReceiptReverse,
    request_id: UUID,
) -> ReceiptResponse:
    try:
        row = load_receipt(session, scope, receipt_id, lock=True)
        if row.status == "reversed" and row.reversal_idempotency_key == payload.idempotency_key:
            return receipt_response(session, row)
        if row.status != "confirmed":
            raise BillingStateError
        allocations = session.scalars(
            select(ReceiptAllocation)
            .where(
                ReceiptAllocation.organization_id == scope.organization_id,
                ReceiptAllocation.receipt_id == row.id,
                ReceiptAllocation.is_active.is_(True),
            )
            .with_for_update()
        ).all()
        statements = [
            load_statement(session, scope, item.statement_id, lock=True) for item in allocations
        ]
        now = datetime.now(UTC)
        row.status = "reversed"
        row.reversed_at = now
        row.reversal_reason = payload.reason
        row.reversal_idempotency_key = payload.idempotency_key
        session.flush()
        session.execute(
            update(ReceiptAllocation)
            .where(
                ReceiptAllocation.organization_id == scope.organization_id,
                ReceiptAllocation.receipt_id == row.id,
            )
            .values(is_active=False)
        )
        session.flush()
        for statement in statements:
            refresh_statement_status(session, statement)
            statement.version += 1
            statement.updated_at = now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="receipt.reverse",
            entity_type="receipt",
            entity_id=row.id,
            document_number=row.document_number,
            reason=payload.reason,
            after={"status": "reversed"},
        )
        session.commit()
        return receipt_response(session, row)
    except IntegrityError:
        session.rollback()
        raise BillingConflictError from None
    except Exception:
        session.rollback()
        raise
