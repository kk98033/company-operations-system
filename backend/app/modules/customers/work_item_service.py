"""Organization-scoped reusable customer work items."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import PageParams
from app.modules.audit import record_user_audit_event
from app.modules.customers.models import Customer, CustomerWorkItem
from app.modules.customers.work_item_schemas import (
    CustomerStatus,
    WorkItemCreate,
    WorkItemResponse,
    WorkItemUpdate,
)
from app.modules.organizations.scope import OrganizationScope


class WorkItemNotFoundError(RuntimeError):
    pass


class WorkItemConflictError(RuntimeError):
    pass


class WorkItemCodeConflictError(RuntimeError):
    pass


def _response(row: CustomerWorkItem) -> WorkItemResponse:
    return WorkItemResponse.model_validate(row, from_attributes=True)


def _customer_exists(session: OrmSession, scope: OrganizationScope, customer_id: UUID) -> bool:
    return (
        session.scalar(
            scope.constrain(select(Customer.id), model=Customer).where(Customer.id == customer_id)
        )
        is not None
    )


def list_work_items(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    page: PageParams,
    keyword: str | None,
    status: CustomerStatus | None,
) -> tuple[list[WorkItemResponse], int]:
    if not _customer_exists(session, scope, customer_id):
        raise WorkItemNotFoundError
    statement = scope.constrain(select(CustomerWorkItem), model=CustomerWorkItem).where(
        CustomerWorkItem.customer_id == customer_id
    )
    if keyword:
        statement = statement.where(
            or_(
                CustomerWorkItem.code.icontains(keyword, autoescape=True),
                CustomerWorkItem.name.icontains(keyword, autoescape=True),
                CustomerWorkItem.specification.icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(CustomerWorkItem.status == status.value)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(func.lower(CustomerWorkItem.name), CustomerWorkItem.id)
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [_response(row) for row in rows], total


def create_work_item(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    payload: WorkItemCreate,
    request_id: UUID,
) -> WorkItemResponse:
    if not _customer_exists(session, scope, customer_id):
        raise WorkItemNotFoundError
    row = CustomerWorkItem(
        **scope.create_values(payload.model_dump()), customer_id=customer_id, source="manual"
    )
    try:
        session.add(row)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="customer_work_item.create",
            entity_type="customer_work_item",
            entity_id=row.id,
            before=None,
            after={"customer_id": str(customer_id), "code": row.code, "name": row.name},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise WorkItemCodeConflictError from None
    return _response(row)


def update_work_item(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    item_id: UUID,
    payload: WorkItemUpdate,
    request_id: UUID,
) -> WorkItemResponse:
    try:
        row = session.scalar(
            scope.constrain(select(CustomerWorkItem), model=CustomerWorkItem)
            .where(CustomerWorkItem.customer_id == customer_id, CustomerWorkItem.id == item_id)
            .with_for_update()
        )
        if row is None:
            raise WorkItemNotFoundError
        if row.updated_at != payload.expected_updated_at:
            raise WorkItemConflictError
        before = {"code": row.code, "name": row.name, "status": row.status}
        for field, value in payload.model_dump(exclude={"expected_updated_at"}).items():
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="customer_work_item.update",
            entity_type="customer_work_item",
            entity_id=row.id,
            before=before,
            after={"code": row.code, "name": row.name, "status": row.status},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise WorkItemCodeConflictError from None
    except Exception:
        session.rollback()
        raise
    return _response(row)


def set_work_item_status(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    item_id: UUID,
    status: CustomerStatus,
    expected_updated_at: datetime,
    request_id: UUID,
) -> WorkItemResponse:
    try:
        row = session.scalar(
            scope.constrain(select(CustomerWorkItem), model=CustomerWorkItem)
            .where(CustomerWorkItem.customer_id == customer_id, CustomerWorkItem.id == item_id)
            .with_for_update()
        )
        if row is None:
            raise WorkItemNotFoundError
        if row.updated_at != expected_updated_at:
            raise WorkItemConflictError
        before = {"status": row.status}
        row.status = status.value
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="customer_work_item.status_update",
            entity_type="customer_work_item",
            entity_id=row.id,
            before=before,
            after={"status": row.status},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _response(row)
