"""Concurrency-safe daily pricing document numbering."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.pricing.errors import PricingConflictError
from app.modules.quotations.models import DocumentSequence


def allocate_pricing_number(session: Session, *, organization_id: UUID, pricing_date: date) -> str:
    period = pricing_date.strftime("%Y%m%d")
    value = session.scalar(
        insert(DocumentSequence)
        .values(
            organization_id=organization_id,
            document_type="pricing",
            period_key=period,
            next_value=2,
        )
        .on_conflict_do_update(
            index_elements=[
                DocumentSequence.organization_id,
                DocumentSequence.document_type,
                DocumentSequence.period_key,
            ],
            set_={"next_value": DocumentSequence.next_value + 1, "updated_at": func.now()},
            where=DocumentSequence.next_value <= 999,
        )
        .returning(DocumentSequence.next_value)
    )
    if value is None or value - 1 > 999:
        raise PricingConflictError
    return f"PRC-{period}-{value - 1:03d}"
