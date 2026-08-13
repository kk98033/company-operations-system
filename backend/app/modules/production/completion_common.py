"""Shared final-completion reads and response mapping."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.organizations.scope import OrganizationScope
from app.modules.production.models import FinalCompletionEntry
from app.modules.production.schemas import FinalCompletionResponse


def completion_response(
    row: FinalCompletionEntry,
    *,
    available: Decimal,
    order_quantity: Decimal,
    completed_total: Decimal | None = None,
) -> FinalCompletionResponse:
    total = completed_total if completed_total is not None else Decimal("0")
    return FinalCompletionResponse(
        id=row.id,
        work_order_id=row.work_order_id,
        entry_type=row.entry_type,
        source_type=row.source_type,
        quantity=row.quantity,
        transport_process_event_id=row.transport_process_event_id,
        reversal_of_id=row.reversal_of_id,
        correlation_id=row.correlation_id,
        reason=row.reason,
        occurred_at=row.occurred_at,
        created_at=row.created_at,
        available_quantity=available,
        exceeds_order_quantity=total > order_quantity,
    )


def find_completion_by_idempotency(
    session: Session, *, scope: OrganizationScope, idempotency_key: UUID
) -> FinalCompletionEntry | None:
    return session.scalar(
        select(FinalCompletionEntry).where(
            FinalCompletionEntry.organization_id == scope.organization_id,
            FinalCompletionEntry.idempotency_key == idempotency_key,
        )
    )


def completed_total(session: Session, *, scope: OrganizationScope, work_order_id: UUID) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(FinalCompletionEntry.quantity), 0)).where(
            FinalCompletionEntry.organization_id == scope.organization_id,
            FinalCompletionEntry.work_order_id == work_order_id,
        )
    ) or Decimal("0")
