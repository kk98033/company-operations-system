"""Concurrency-safe daily case and work-order numbering."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.quotations.models import DocumentSequence
from app.modules.work_orders.errors import WorkOrderNumberExhaustedError

PREFIXES = {"case": "CASE", "work_order": "WO"}


def allocate_number(
    session: Session,
    *,
    organization_id: UUID,
    document_type: str,
    document_date: date,
) -> str:
    if document_type not in PREFIXES:
        raise ValueError("unsupported document type")
    period = document_date.strftime("%Y%m%d")
    statement = (
        insert(DocumentSequence)
        .values(
            organization_id=organization_id,
            document_type=document_type,
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
    next_value = session.scalar(statement)
    if next_value is None or next_value - 1 > 999:
        raise WorkOrderNumberExhaustedError
    return f"{PREFIXES[document_type]}-{period}-{next_value - 1:03d}"
