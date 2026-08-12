"""Vendor queries and audited commands."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import PageParams
from app.modules.audit import record_user_audit_event
from app.modules.master_data.errors import (
    MasterConflictError,
    MasterDuplicateError,
    MasterNotFoundError,
)
from app.modules.master_data.models import Vendor
from app.modules.master_data.schemas import MasterStatus, VendorCreate, VendorResponse, VendorUpdate
from app.modules.organizations.scope import OrganizationScope


def _response(row: Vendor) -> VendorResponse:
    return VendorResponse.model_validate(row, from_attributes=True)


def list_vendors(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: MasterStatus | None,
) -> tuple[list[VendorResponse], int]:
    statement = scope.constrain(select(Vendor), model=Vendor)
    if keyword:
        statement = statement.where(
            or_(
                Vendor.code.icontains(keyword, autoescape=True),
                Vendor.name.icontains(keyword, autoescape=True),
                Vendor.short_name.icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(Vendor.status == status.value)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(func.lower(func.btrim(Vendor.code)), Vendor.id)
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [_response(row) for row in rows], total


def create_vendor(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    payload: VendorCreate,
    request_id: UUID,
) -> VendorResponse:
    row = Vendor(**scope.create_values(payload.model_dump()))
    try:
        session.add(row)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="vendor.create",
            entity_type="vendor",
            entity_id=row.id,
            before=None,
            after={"code": row.code, "name": row.name, "category": row.category},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise MasterDuplicateError from None
    return _response(row)


def update_vendor(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    vendor_id: UUID,
    payload: VendorUpdate,
    request_id: UUID,
) -> VendorResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Vendor), model=Vendor)
            .where(Vendor.id == vendor_id)
            .with_for_update()
        )
        if row is None:
            raise MasterNotFoundError
        if row.updated_at != payload.expected_updated_at:
            raise MasterConflictError
        before = {
            "code": row.code,
            "name": row.name,
            "category": row.category,
            "status": row.status,
        }
        for field, value in payload.model_dump(exclude={"expected_updated_at"}).items():
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="vendor.update",
            entity_type="vendor",
            entity_id=row.id,
            before=before,
            after={
                "code": row.code,
                "name": row.name,
                "category": row.category,
                "status": row.status,
            },
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise MasterDuplicateError from None
    except Exception:
        session.rollback()
        raise
    return _response(row)


def set_vendor_status(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    vendor_id: UUID,
    status: MasterStatus,
    expected_updated_at: datetime,
    request_id: UUID,
) -> VendorResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Vendor), model=Vendor)
            .where(Vendor.id == vendor_id)
            .with_for_update()
        )
        if row is None:
            raise MasterNotFoundError
        if row.updated_at != expected_updated_at:
            raise MasterConflictError
        before = {"status": row.status}
        row.status = status.value
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="vendor.status_update",
            entity_type="vendor",
            entity_id=row.id,
            before=before,
            after={"status": row.status},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _response(row)
