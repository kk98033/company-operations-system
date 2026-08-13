"""Work-order CRUD, lifecycle, search, and print snapshot."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.contracts import PageParams
from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.work_orders.case_service import create_case_row, work_order_summary
from app.modules.work_orders.errors import (
    WorkOrderConflictError,
    WorkOrderNotFoundError,
    WorkOrderNumberExhaustedError,
    WorkOrderStateError,
)
from app.modules.work_orders.models import ProductionCase, WorkOrder
from app.modules.work_orders.numbering import allocate_number
from app.modules.work_orders.schemas import (
    CaseCreate,
    WorkOrderCreate,
    WorkOrderResponse,
    WorkOrderStatus,
    WorkOrderSummary,
    WorkOrderUpdate,
)
from app.modules.work_orders.snapshots import load_snapshots


def work_order_response(row: WorkOrder) -> WorkOrderResponse:
    data = {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
        if column.name not in {"organization_id", "legacy_source_table", "legacy_source_key"}
    }
    return WorkOrderResponse.model_validate(data)


def _write_values(payload: WorkOrderCreate | WorkOrderUpdate) -> dict[str, object]:
    """Keep database scalar types while making JSON columns JSON-safe."""
    values = payload.model_dump(exclude={"case_id", "expected_updated_at"}, mode="python")
    values["papers"] = [item.model_dump(mode="json") for item in payload.papers]
    values["print_specification"] = payload.print_specification.model_dump(mode="json")
    values["processes"] = [item.model_dump(mode="json") for item in payload.processes]
    return values


def _case_for_order(
    session: Session, *, scope: OrganizationScope, payload: WorkOrderCreate
) -> ProductionCase:
    if payload.case_id is None:
        return create_case_row(
            session,
            scope=scope,
            payload=CaseCreate(
                case_date=payload.order_date,
                customer_id=payload.customer_id,
                notes=None,
            ),
        )
    row = session.scalar(
        scope.constrain(select(ProductionCase), model=ProductionCase).where(
            ProductionCase.id == payload.case_id
        )
    )
    if row is None:
        raise WorkOrderNotFoundError
    if row.status == "void" or row.customer_id != payload.customer_id:
        raise WorkOrderStateError
    return row


def create_work_order_row(
    session: Session,
    *,
    scope: OrganizationScope,
    payload: WorkOrderCreate,
    case: ProductionCase | None = None,
    source_quotation_item_id: UUID | None = None,
) -> WorkOrder:
    parent = case or _case_for_order(session, scope=scope, payload=payload)
    organization_snapshot, customer_snapshot = load_snapshots(
        session, scope=scope, customer_id=payload.customer_id
    )
    row = WorkOrder(
        organization_id=scope.organization_id,
        case_id=parent.id,
        document_number=allocate_number(
            session,
            organization_id=scope.organization_id,
            document_type="work_order",
            document_date=payload.order_date,
        ),
        organization_snapshot=organization_snapshot,
        customer_snapshot=customer_snapshot,
        source_quotation_item_id=source_quotation_item_id,
        **_write_values(payload),
    )
    session.add(row)
    session.flush()
    return row


def create_work_order(
    session: Session,
    *,
    scope: OrganizationScope,
    payload: WorkOrderCreate,
    request_id: UUID,
) -> WorkOrderResponse:
    try:
        row = create_work_order_row(session, scope=scope, payload=payload)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="work_order.create",
            entity_type="work_order",
            entity_id=row.id,
            document_number=row.document_number,
            before=None,
            after={"status": row.status, "case_id": str(row.case_id)},
        )
        session.commit()
    except (WorkOrderNotFoundError, WorkOrderStateError, WorkOrderNumberExhaustedError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise WorkOrderConflictError from None
    return work_order_response(row)


def list_work_orders(
    session: Session,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: WorkOrderStatus | None,
) -> tuple[list[WorkOrderSummary], int]:
    statement = scope.constrain(select(WorkOrder), model=WorkOrder)
    if keyword:
        statement = statement.where(
            or_(
                WorkOrder.document_number.icontains(keyword, autoescape=True),
                WorkOrder.legacy_document_number.icontains(keyword, autoescape=True),
                WorkOrder.customer_order_number.icontains(keyword, autoescape=True),
                WorkOrder.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
                WorkOrder.product_name.icontains(keyword, autoescape=True),
                WorkOrder.specification.icontains(keyword, autoescape=True),
                WorkOrder.notes.icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(WorkOrder.status == status.value)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(WorkOrder.order_date.desc(), WorkOrder.document_number.desc())
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [work_order_summary(row) for row in rows], total


def get_work_order(
    session: Session, *, scope: OrganizationScope, work_order_id: UUID
) -> WorkOrderResponse:
    row = session.scalar(
        scope.constrain(select(WorkOrder), model=WorkOrder).where(WorkOrder.id == work_order_id)
    )
    if row is None:
        raise WorkOrderNotFoundError
    return work_order_response(row)


def update_work_order(
    session: Session,
    *,
    scope: OrganizationScope,
    work_order_id: UUID,
    payload: WorkOrderUpdate,
    request_id: UUID,
) -> WorkOrderResponse:
    try:
        row = session.scalar(
            scope.constrain(select(WorkOrder), model=WorkOrder)
            .where(WorkOrder.id == work_order_id)
            .with_for_update()
        )
        if row is None:
            raise WorkOrderNotFoundError
        if row.status != "draft":
            raise WorkOrderStateError
        if row.updated_at != payload.expected_updated_at:
            raise WorkOrderConflictError
        if row.customer_id != payload.customer_id:
            raise WorkOrderStateError
        for field, value in _write_values(payload).items():
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="work_order.update",
            entity_type="work_order",
            entity_id=row.id,
            document_number=row.document_number,
            before=None,
            after={"status": row.status},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return work_order_response(row)
