"""Scoped customer queries and audited commands."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import PageParams, SortDirection
from app.modules.audit import record_user_audit_event
from app.modules.customers.models import Customer
from app.modules.customers.schemas import (
    CustomerCreate,
    CustomerResponse,
    CustomerSortField,
    CustomerSortParams,
    CustomerStatus,
    CustomerUpdate,
)
from app.modules.organizations.scope import OrganizationScope


class CustomerNotFoundError(RuntimeError):
    pass


class CustomerConflictError(RuntimeError):
    pass


class CustomerCodeConflictError(RuntimeError):
    pass


def _response(row: Customer) -> CustomerResponse:
    return CustomerResponse.model_validate(row, from_attributes=True)


def list_customers(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: CustomerStatus | None,
    sort: CustomerSortParams,
) -> tuple[list[CustomerResponse], int]:
    statement = scope.constrain(select(Customer), model=Customer)
    if keyword:
        statement = statement.where(
            or_(
                Customer.code.icontains(keyword, autoescape=True),
                Customer.name.icontains(keyword, autoescape=True),
                Customer.short_name.icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(Customer.status == status.value)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    column = {
        CustomerSortField.CODE: func.lower(func.btrim(Customer.code)),
        CustomerSortField.NAME: Customer.name,
        CustomerSortField.UPDATED_AT: Customer.updated_at,
    }[sort.sort_by]
    direction = column.asc if sort.sort_direction is SortDirection.ASC else column.desc
    rows = session.scalars(
        statement.order_by(direction(), Customer.id.asc())
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [_response(row) for row in rows], total


def get_customer(
    session: OrmSession, *, scope: OrganizationScope, customer_id: UUID
) -> CustomerResponse:
    row = session.scalar(
        scope.constrain(select(Customer), model=Customer).where(Customer.id == customer_id)
    )
    if row is None:
        raise CustomerNotFoundError
    return _response(row)


def create_customer(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    payload: CustomerCreate,
    request_id: UUID,
) -> CustomerResponse:
    row = Customer(**scope.create_values(payload.model_dump()))
    try:
        session.add(row)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="customer.create",
            entity_type="customer",
            entity_id=row.id,
            before=None,
            after={"code": row.code, "name": row.name, "status": row.status},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise CustomerCodeConflictError from None
    return _response(row)


def update_customer(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    payload: CustomerUpdate,
    request_id: UUID,
) -> CustomerResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Customer), model=Customer)
            .where(Customer.id == customer_id)
            .with_for_update()
        )
        if row is None:
            raise CustomerNotFoundError
        if row.updated_at != payload.expected_updated_at:
            raise CustomerConflictError
        before = {"code": row.code, "name": row.name, "status": row.status}
        for field, value in payload.model_dump(exclude={"expected_updated_at"}).items():
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="customer.update",
            entity_type="customer",
            entity_id=row.id,
            before=before,
            after={"code": row.code, "name": row.name, "status": row.status},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise CustomerCodeConflictError from None
    except Exception:
        session.rollback()
        raise
    return _response(row)


def set_customer_status(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    customer_id: UUID,
    status: CustomerStatus,
    expected_updated_at: datetime,
    request_id: UUID,
) -> CustomerResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Customer), model=Customer)
            .where(Customer.id == customer_id)
            .with_for_update()
        )
        if row is None:
            raise CustomerNotFoundError
        if row.updated_at != expected_updated_at:
            raise CustomerConflictError
        before = {"status": row.status}
        row.status = status.value
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="customer.status_update",
            entity_type="customer",
            entity_id=row.id,
            before=before,
            after={"status": row.status},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _response(row)
