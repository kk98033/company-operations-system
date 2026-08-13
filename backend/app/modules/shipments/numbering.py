"""Concurrency-safe monthly shipment numbering."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.quotations.models import DocumentSequence
from app.modules.shipments.errors import ShipmentConflictError


def allocate_shipment_number(
    session: Session, *, organization_id: UUID, shipment_date: date
) -> str:
    period = shipment_date.strftime("%Y%m")
    statement = (
        insert(DocumentSequence)
        .values(
            organization_id=organization_id,
            document_type="shipment",
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
    value = session.scalar(statement)
    if value is None or value - 1 > 999:
        raise ShipmentConflictError
    return f"SHP-{period}-{value - 1:03d}"
