"""Legal append-only transitions for the fixed thirteen work-order processes."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.production.common import locked_confirmed_order
from app.modules.production.errors import ProductionConflictError, ProductionStateError
from app.modules.production.models import ProcessEvent
from app.modules.production.schemas import (
    PROCESS_NAME_BY_CODE,
    ProcessEventCreate,
    ProcessEventResponse,
)

STATE_BY_EVENT = {
    None: "not_started",
    "start": "in_progress",
    "partial_complete": "partial",
    "complete": "completed",
    "reopen": "in_progress",
}
ALLOWED = {
    "not_started": {"start"},
    "in_progress": {"partial_complete", "complete"},
    "partial": {"partial_complete", "complete"},
    "completed": {"reopen"},
}


def event_response(row: ProcessEvent) -> ProcessEventResponse:
    return ProcessEventResponse(
        id=row.id,
        work_order_id=row.work_order_id,
        process_code=row.process_code,
        process_name=PROCESS_NAME_BY_CODE[row.process_code],
        event_type=row.event_type,
        sequence_no=row.sequence_no,
        completed_quantity=row.completed_quantity,
        reason=row.reason,
        occurred_at=row.occurred_at,
        created_at=row.created_at,
    )


def record_process_event(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    payload: ProcessEventCreate,
    request_id: UUID,
) -> ProcessEventResponse:
    existing = session.scalar(
        select(ProcessEvent).where(
            ProcessEvent.organization_id == scope.organization_id,
            ProcessEvent.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        if (
            existing.work_order_id == work_order_id
            and existing.process_code == payload.process_code.value
            and existing.event_type == payload.event_type.value
        ):
            return event_response(existing)
        raise ProductionConflictError
    try:
        locked_confirmed_order(session, scope=scope, work_order_id=work_order_id)
        concurrent = session.scalar(
            select(ProcessEvent).where(
                ProcessEvent.organization_id == scope.organization_id,
                ProcessEvent.idempotency_key == payload.idempotency_key,
            )
        )
        if concurrent is not None:
            if (
                concurrent.work_order_id != work_order_id
                or concurrent.process_code != payload.process_code.value
                or concurrent.event_type != payload.event_type.value
            ):
                raise ProductionConflictError
            response = event_response(concurrent)
            session.rollback()
            return response
        latest = session.scalar(
            select(ProcessEvent)
            .where(
                ProcessEvent.organization_id == scope.organization_id,
                ProcessEvent.work_order_id == work_order_id,
                ProcessEvent.process_code == payload.process_code.value,
            )
            .order_by(ProcessEvent.sequence_no.desc())
            .limit(1)
        )
        state = STATE_BY_EVENT[latest.event_type if latest else None]
        if payload.event_type.value not in ALLOWED[state]:
            raise ProductionStateError
        sequence = (
            session.scalar(
                select(func.coalesce(func.max(ProcessEvent.sequence_no), 0)).where(
                    ProcessEvent.organization_id == scope.organization_id,
                    ProcessEvent.work_order_id == work_order_id,
                    ProcessEvent.process_code == payload.process_code.value,
                )
            )
            + 1
        )
        row = ProcessEvent(
            organization_id=scope.organization_id,
            work_order_id=work_order_id,
            process_code=payload.process_code.value,
            event_type=payload.event_type.value,
            sequence_no=sequence,
            completed_quantity=payload.completed_quantity,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
            actor_membership_id=scope.organization_member_id,
            actor_user_id=scope.actor_user_id,
            occurred_at=datetime.now(UTC),
        )
        session.add(row)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="production.process_event",
            entity_type="process_event",
            entity_id=row.id,
            after={
                "work_order_id": str(work_order_id),
                "process": row.process_code,
                "event": row.event_type,
            },
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ProductionConflictError from None
    except Exception:
        session.rollback()
        raise
    return event_response(row)
