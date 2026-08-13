"""Production-case commands and query summaries."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.contracts import PageParams
from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.work_orders.errors import (
    WorkOrderConflictError,
    WorkOrderNotFoundError,
    WorkOrderStateError,
)
from app.modules.work_orders.models import ProductionCase, WorkOrder
from app.modules.work_orders.numbering import allocate_number
from app.modules.work_orders.schemas import (
    CaseCreate,
    CaseResponse,
    CaseStatus,
    CaseSummary,
    CaseUpdate,
    WorkOrderSummary,
)
from app.modules.work_orders.snapshots import load_snapshots


def work_order_summary(row: WorkOrder) -> WorkOrderSummary:
    return WorkOrderSummary(
        id=row.id,
        case_id=row.case_id,
        document_number=row.document_number,
        legacy_document_number=row.legacy_document_number,
        order_date=row.order_date,
        delivery_date=row.delivery_date,
        customer_order_number=row.customer_order_number,
        customer_name=str(row.customer_snapshot.get("name") or ""),
        product_name=row.product_name,
        order_quantity=row.order_quantity,
        unit_price=row.unit_price,
        plate_fee=row.plate_fee,
        die_fee=row.die_fee,
        status=row.status,
    )


def _orders(session: Session, row: ProductionCase) -> list[WorkOrder]:
    return list(
        session.scalars(
            select(WorkOrder)
            .where(
                WorkOrder.organization_id == row.organization_id,
                WorkOrder.case_id == row.id,
            )
            .order_by(WorkOrder.document_number)
        ).all()
    )


def case_response(session: Session, row: ProductionCase) -> CaseResponse:
    return CaseResponse(
        id=row.id,
        case_number=row.case_number,
        case_date=row.case_date,
        customer_id=row.customer_id,
        customer_snapshot=row.customer_snapshot,
        status=row.status,
        notes=row.notes,
        source_quotation_id=row.source_quotation_id,
        legacy_document_number=row.legacy_document_number,
        voided_at=row.voided_at,
        void_reason=row.void_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
        work_orders=[work_order_summary(item) for item in _orders(session, row)],
    )


def create_case_row(
    session: Session,
    *,
    scope: OrganizationScope,
    payload: CaseCreate,
    source_quotation_id: UUID | None = None,
) -> ProductionCase:
    organization_snapshot, customer_snapshot = load_snapshots(
        session, scope=scope, customer_id=payload.customer_id
    )
    row = ProductionCase(
        organization_id=scope.organization_id,
        case_number=allocate_number(
            session,
            organization_id=scope.organization_id,
            document_type="case",
            document_date=payload.case_date,
        ),
        case_date=payload.case_date,
        customer_id=payload.customer_id,
        organization_snapshot=organization_snapshot,
        customer_snapshot=customer_snapshot,
        notes=payload.notes,
        source_quotation_id=source_quotation_id,
    )
    session.add(row)
    session.flush()
    return row


def create_case(
    session: Session,
    *,
    scope: OrganizationScope,
    payload: CaseCreate,
    request_id: UUID,
) -> CaseResponse:
    try:
        row = create_case_row(session, scope=scope, payload=payload)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="case.create",
            entity_type="production_case",
            entity_id=row.id,
            document_number=row.case_number,
            before=None,
            after={"status": row.status},
        )
        session.commit()
    except (WorkOrderNotFoundError, WorkOrderConflictError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise WorkOrderConflictError from None
    return case_response(session, row)


def list_cases(
    session: Session,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: CaseStatus | None,
) -> tuple[list[CaseSummary], int]:
    statement = scope.constrain(select(ProductionCase), model=ProductionCase)
    if keyword:
        statement = statement.where(
            or_(
                ProductionCase.case_number.icontains(keyword, autoescape=True),
                ProductionCase.legacy_document_number.icontains(keyword, autoescape=True),
                ProductionCase.customer_snapshot["name"]
                .as_string()
                .icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(ProductionCase.status == status.value)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(ProductionCase.case_date.desc(), ProductionCase.case_number.desc())
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    summaries = []
    for row in rows:
        orders = _orders(session, row)
        summaries.append(
            CaseSummary(
                id=row.id,
                case_number=row.case_number,
                case_date=row.case_date,
                customer_name=str(row.customer_snapshot.get("name") or ""),
                status=row.status,
                work_order_count=len(orders),
                confirmed_count=sum(item.status == "confirmed" for item in orders),
                updated_at=row.updated_at,
            )
        )
    return summaries, total


def get_case(session: Session, *, scope: OrganizationScope, case_id: UUID) -> CaseResponse:
    row = session.scalar(
        scope.constrain(select(ProductionCase), model=ProductionCase).where(
            ProductionCase.id == case_id
        )
    )
    if row is None:
        raise WorkOrderNotFoundError
    return case_response(session, row)


def update_case(
    session: Session,
    *,
    scope: OrganizationScope,
    case_id: UUID,
    payload: CaseUpdate,
    request_id: UUID,
) -> CaseResponse:
    try:
        row = session.scalar(
            scope.constrain(select(ProductionCase), model=ProductionCase)
            .where(ProductionCase.id == case_id)
            .with_for_update()
        )
        if row is None:
            raise WorkOrderNotFoundError
        if row.status == "void":
            raise WorkOrderStateError
        if row.updated_at != payload.expected_updated_at:
            raise WorkOrderConflictError
        if row.customer_id != payload.customer_id and _orders(session, row):
            raise WorkOrderStateError
        if row.customer_id != payload.customer_id:
            row.organization_snapshot, row.customer_snapshot = load_snapshots(
                session, scope=scope, customer_id=payload.customer_id
            )
        row.case_date, row.customer_id, row.notes = (
            payload.case_date,
            payload.customer_id,
            payload.notes,
        )
        row.updated_at = datetime.now(UTC)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="case.update",
            entity_type="production_case",
            entity_id=row.id,
            document_number=row.case_number,
            before=None,
            after={"status": row.status},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case_response(session, row)


def void_case(
    session: Session,
    *,
    scope: OrganizationScope,
    case_id: UUID,
    expected_updated_at: datetime,
    reason: str,
    request_id: UUID,
) -> CaseResponse:
    try:
        row = session.scalar(
            scope.constrain(select(ProductionCase), model=ProductionCase)
            .where(ProductionCase.id == case_id)
            .with_for_update()
        )
        if row is None:
            raise WorkOrderNotFoundError
        if row.status == "void" or row.updated_at != expected_updated_at:
            raise WorkOrderConflictError
        if any(item.status != "void" for item in _orders(session, row)):
            raise WorkOrderStateError
        row.status, row.voided_at, row.void_reason = "void", datetime.now(UTC), reason
        row.updated_at = row.voided_at
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="case.void",
            entity_type="production_case",
            entity_id=row.id,
            document_number=row.case_number,
            before=None,
            after={"status": "void", "reason": reason},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case_response(session, row)
