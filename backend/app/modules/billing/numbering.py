"""Concurrency-safe statement and receipt numbering."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.billing.errors import BillingConflictError
from app.modules.quotations.models import DocumentSequence


def _allocate(session: Session, organization_id: UUID, kind: str, period: str, limit: int) -> int:
    value = session.scalar(
        insert(DocumentSequence)
        .values(
            organization_id=organization_id, document_type=kind, period_key=period, next_value=2
        )
        .on_conflict_do_update(
            index_elements=[
                DocumentSequence.organization_id,
                DocumentSequence.document_type,
                DocumentSequence.period_key,
            ],
            set_={"next_value": DocumentSequence.next_value + 1, "updated_at": func.now()},
            where=DocumentSequence.next_value <= limit,
        )
        .returning(DocumentSequence.next_value)
    )
    if value is None or value - 1 > limit:
        raise BillingConflictError
    return value - 1


def allocate_statement_number(session: Session, organization_id: UUID, day: date) -> str:
    period = day.strftime("%Y%m")
    return f"STM-{period}-{_allocate(session, organization_id, 'statement', period, 999):03d}"


def allocate_receipt_number(session: Session, organization_id: UUID, day: date) -> str:
    period = day.strftime("%Y%m%d")
    return f"RCT-{period}-{_allocate(session, organization_id, 'receipt', period, 999):03d}"
