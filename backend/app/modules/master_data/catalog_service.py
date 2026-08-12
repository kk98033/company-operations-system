"""Paper catalogs and fixed process definition commands."""

from datetime import UTC, datetime
from typing import Literal
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
from app.modules.master_data.models import PaperMill, PaperType, ProcessDefinition
from app.modules.master_data.schemas import (
    CatalogCreate,
    CatalogResponse,
    CatalogUpdate,
    MasterStatus,
    ProcessDefinitionResponse,
)
from app.modules.organizations.scope import OrganizationScope

CatalogKind = Literal["paper_type", "paper_mill"]
CatalogModel = type[PaperType] | type[PaperMill]


def _model(kind: CatalogKind) -> CatalogModel:
    return PaperType if kind == "paper_type" else PaperMill


def list_catalog(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    kind: CatalogKind,
    page: PageParams,
    keyword: str | None,
    status: MasterStatus | None,
) -> tuple[list[CatalogResponse], int]:
    model = _model(kind)
    statement = scope.constrain(select(model), model=model)
    if keyword:
        statement = statement.where(
            or_(
                model.code.icontains(keyword, autoescape=True),
                model.name.icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(model.status == status.value)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(model.sort_order, func.lower(model.name), model.id)
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    return [CatalogResponse.model_validate(row, from_attributes=True) for row in rows], total


def create_catalog(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    kind: CatalogKind,
    payload: CatalogCreate,
    request_id: UUID,
) -> CatalogResponse:
    model = _model(kind)
    row = model(**scope.create_values(payload.model_dump()))
    try:
        session.add(row)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action=f"{kind}.create",
            entity_type=kind,
            entity_id=row.id,
            before=None,
            after={"code": row.code, "name": row.name, "sort_order": row.sort_order},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise MasterDuplicateError from None
    return CatalogResponse.model_validate(row, from_attributes=True)


def update_catalog(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    kind: CatalogKind,
    item_id: UUID,
    payload: CatalogUpdate,
    request_id: UUID,
) -> CatalogResponse:
    model = _model(kind)
    try:
        row = session.scalar(
            scope.constrain(select(model), model=model).where(model.id == item_id).with_for_update()
        )
        if row is None:
            raise MasterNotFoundError
        if row.updated_at != payload.expected_updated_at:
            raise MasterConflictError
        before = {"code": row.code, "name": row.name, "sort_order": row.sort_order}
        for field, value in payload.model_dump(exclude={"expected_updated_at"}).items():
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action=f"{kind}.update",
            entity_type=kind,
            entity_id=row.id,
            before=before,
            after={"code": row.code, "name": row.name, "sort_order": row.sort_order},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise MasterDuplicateError from None
    except Exception:
        session.rollback()
        raise
    return CatalogResponse.model_validate(row, from_attributes=True)


def set_catalog_status(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    kind: CatalogKind,
    item_id: UUID,
    status: MasterStatus,
    expected_updated_at: datetime,
    request_id: UUID,
) -> CatalogResponse:
    model = _model(kind)
    row = _set_status(
        session,
        scope=scope,
        model=model,
        item_id=item_id,
        status=status,
        expected_updated_at=expected_updated_at,
        request_id=request_id,
        entity_type=kind,
    )
    return CatalogResponse.model_validate(row, from_attributes=True)


def list_processes(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    status: MasterStatus | None,
) -> list[ProcessDefinitionResponse]:
    statement = scope.constrain(select(ProcessDefinition), model=ProcessDefinition)
    if status:
        statement = statement.where(ProcessDefinition.status == status.value)
    rows = session.scalars(statement.order_by(ProcessDefinition.sort_order)).all()
    return [ProcessDefinitionResponse.model_validate(row, from_attributes=True) for row in rows]


def set_process_status(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    item_id: UUID,
    status: MasterStatus,
    expected_updated_at: datetime,
    request_id: UUID,
) -> ProcessDefinitionResponse:
    row = _set_status(
        session,
        scope=scope,
        model=ProcessDefinition,
        item_id=item_id,
        status=status,
        expected_updated_at=expected_updated_at,
        request_id=request_id,
        entity_type="process_definition",
    )
    return ProcessDefinitionResponse.model_validate(row, from_attributes=True)


def _set_status(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    model: CatalogModel | type[ProcessDefinition],
    item_id: UUID,
    status: MasterStatus,
    expected_updated_at: datetime,
    request_id: UUID,
    entity_type: str,
):
    try:
        row = session.scalar(
            scope.constrain(select(model), model=model).where(model.id == item_id).with_for_update()
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
            action=f"{entity_type}.status_update",
            entity_type=entity_type,
            entity_id=row.id,
            before=before,
            after={"status": row.status},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return row
