"""Scoped quotation queries and commands."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.api.contracts import PageParams
from app.modules.audit import record_user_audit_event
from app.modules.customers.models import Customer
from app.modules.organizations.models import Organization
from app.modules.organizations.scope import OrganizationScope
from app.modules.quotations.errors import (
    QuotationConflictError,
    QuotationNotFoundError,
    QuotationNumberExhaustedError,
    QuotationStateError,
)
from app.modules.quotations.models import DocumentSequence, Quotation, QuotationItem
from app.modules.quotations.schemas import (
    QuotationCreate,
    QuotationItemResponse,
    QuotationResponse,
    QuotationStatus,
    QuotationSummary,
    QuotationUpdate,
)


def _allocate_number(session: OrmSession, organization_id: UUID, quotation_date: date) -> str:
    period = quotation_date.strftime("%Y%m%d")
    statement = (
        insert(DocumentSequence)
        .values(
            organization_id=organization_id,
            document_type="quotation",
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
            where=DocumentSequence.next_value <= 99,
        )
        .returning(DocumentSequence.next_value)
    )
    next_value = session.scalar(statement)
    if next_value is None:
        raise QuotationNumberExhaustedError
    allocated = next_value - 1
    if allocated > 99:
        raise QuotationNumberExhaustedError
    return f"QUO-{period}-{allocated:02d}"


def _snapshots(
    session: OrmSession, scope: OrganizationScope, customer_id: UUID
) -> tuple[dict, dict]:
    organization = session.get(Organization, scope.organization_id)
    customer = session.scalar(
        scope.constrain(select(Customer), model=Customer).where(
            Customer.id == customer_id, Customer.status == "active"
        )
    )
    if organization is None or customer is None:
        raise QuotationNotFoundError
    return (
        {
            "name": organization.name,
            "tax_identifier": organization.tax_identifier,
            "representative_name": organization.representative_name,
            "phone": organization.phone,
            "fax": organization.fax,
            "email": organization.email,
            "address": organization.address,
        },
        {
            "code": customer.code,
            "name": customer.name,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
            "fax": customer.fax,
            "address": customer.address,
            "tax_identifier": customer.tax_identifier,
        },
    )


def _items(session: OrmSession, row: Quotation) -> list[QuotationItem]:
    return list(
        session.scalars(
            select(QuotationItem)
            .where(
                QuotationItem.organization_id == row.organization_id,
                QuotationItem.quotation_id == row.id,
            )
            .order_by(QuotationItem.line_number)
        ).all()
    )


def _response(session: OrmSession, row: Quotation) -> QuotationResponse:
    data = {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
        if column.name != "organization_id"
    }
    data["items"] = [
        QuotationItemResponse.model_validate(item, from_attributes=True)
        for item in _items(session, row)
    ]
    return QuotationResponse.model_validate(data)


def list_quotations(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    page: PageParams,
    keyword: str | None,
    status: QuotationStatus | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[QuotationSummary], int]:
    statement = scope.constrain(select(Quotation), model=Quotation)
    if keyword:
        statement = statement.where(
            or_(
                Quotation.document_number.icontains(keyword, autoescape=True),
                Quotation.legacy_document_number.icontains(keyword, autoescape=True),
                Quotation.customer_snapshot["name"].as_string().icontains(keyword, autoescape=True),
            )
        )
    if status:
        statement = statement.where(Quotation.status == status.value)
    if date_from:
        statement = statement.where(Quotation.quotation_date >= date_from)
    if date_to:
        statement = statement.where(Quotation.quotation_date <= date_to)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(Quotation.quotation_date.desc(), Quotation.document_number.desc())
        .offset(page.offset)
        .limit(page.page_size)
    ).all()
    result = []
    for row in rows:
        items = _items(session, row)
        result.append(
            QuotationSummary(
                id=row.id,
                document_number=row.document_number,
                legacy_document_number=row.legacy_document_number,
                quotation_date=row.quotation_date,
                customer_name=str(row.customer_snapshot.get("name") or ""),
                first_product_name=items[0].product_name if items else "",
                item_count=len(items),
                status=row.status,
                updated_at=row.updated_at,
            )
        )
    return result, total


def get_quotation(
    session: OrmSession, *, scope: OrganizationScope, quotation_id: UUID
) -> QuotationResponse:
    row = session.scalar(
        scope.constrain(select(Quotation), model=Quotation).where(Quotation.id == quotation_id)
    )
    if row is None:
        raise QuotationNotFoundError
    return _response(session, row)


def _replace_items(session: OrmSession, row: Quotation, items: list) -> None:
    session.execute(
        delete(QuotationItem).where(
            QuotationItem.quotation_id == row.id,
            QuotationItem.organization_id == row.organization_id,
        )
    )
    session.add_all(
        [
            QuotationItem(
                organization_id=row.organization_id,
                quotation_id=row.id,
                line_number=index,
                **item.model_dump(),
            )
            for index, item in enumerate(items, 1)
        ]
    )


def create_quotation(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    payload: QuotationCreate,
    request_id: UUID,
    source: Quotation | None = None,
) -> QuotationResponse:
    try:
        organization_snapshot, customer_snapshot = _snapshots(session, scope, payload.customer_id)
        row = Quotation(
            organization_id=scope.organization_id,
            document_number=_allocate_number(
                session, scope.organization_id, payload.quotation_date
            ),
            quotation_date=payload.quotation_date,
            customer_id=payload.customer_id,
            organization_snapshot=organization_snapshot,
            customer_snapshot=customer_snapshot,
            notes=payload.notes,
            source_quotation_id=source.id if source else None,
        )
        session.add(row)
        session.flush()
        _replace_items(session, row, payload.items)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="quotation.create",
            entity_type="quotation",
            entity_id=row.id,
            document_number=row.document_number,
            before=None,
            after={"status": row.status, "item_count": len(payload.items)},
        )
        session.commit()
    except (QuotationNotFoundError, QuotationNumberExhaustedError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise QuotationConflictError from None
    return _response(session, row)


def update_quotation(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    quotation_id: UUID,
    payload: QuotationUpdate,
    request_id: UUID,
) -> QuotationResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Quotation), model=Quotation)
            .where(Quotation.id == quotation_id)
            .with_for_update()
        )
        if row is None:
            raise QuotationNotFoundError
        if row.status != "draft":
            raise QuotationStateError
        if row.updated_at != payload.expected_updated_at:
            raise QuotationConflictError
        if row.customer_id != payload.customer_id:
            row.organization_snapshot, row.customer_snapshot = _snapshots(
                session, scope, payload.customer_id
            )
        before = {"status": row.status, "item_count": len(_items(session, row))}
        row.quotation_date = payload.quotation_date
        row.customer_id = payload.customer_id
        row.notes = payload.notes
        row.updated_at = datetime.now(UTC)
        _replace_items(session, row, payload.items)
        session.flush()
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="quotation.update",
            entity_type="quotation",
            entity_id=row.id,
            document_number=row.document_number,
            before=before,
            after={"status": row.status, "item_count": len(payload.items)},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _response(session, row)


def confirm_quotation(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    quotation_id: UUID,
    expected_updated_at: datetime,
    request_id: UUID,
) -> QuotationResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Quotation), model=Quotation)
            .where(Quotation.id == quotation_id)
            .with_for_update()
        )
        if row is None:
            raise QuotationNotFoundError
        if row.status != "draft":
            raise QuotationStateError
        if row.updated_at != expected_updated_at:
            raise QuotationConflictError
        now = datetime.now(UTC)
        response = _response(session, row)
        row.document_snapshot = response.model_dump(
            mode="json",
            exclude={
                "document_snapshot",
                "print_metadata",
                "confirmed_at",
                "updated_at",
                "created_at",
            },
        )
        row.print_metadata = {
            "paper_size": "A4",
            "orientation": "landscape",
            "layout_version": "gmail-a4-landscape-v1",
            "captured_at": now.isoformat(),
        }
        row.status = "confirmed"
        row.confirmed_at = now
        row.updated_at = now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="quotation.confirm",
            entity_type="quotation",
            entity_id=row.id,
            document_number=row.document_number,
            before={"status": "draft"},
            after={"status": "confirmed"},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _response(session, row)


def void_quotation(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    quotation_id: UUID,
    expected_updated_at: datetime,
    reason: str,
    request_id: UUID,
) -> QuotationResponse:
    try:
        row = session.scalar(
            scope.constrain(select(Quotation), model=Quotation)
            .where(Quotation.id == quotation_id)
            .with_for_update()
        )
        if row is None:
            raise QuotationNotFoundError
        if row.status == "void":
            raise QuotationStateError
        if row.updated_at != expected_updated_at:
            raise QuotationConflictError
        now = datetime.now(UTC)
        previous_status = row.status
        row.status = "void"
        row.voided_at = now
        row.void_reason = reason
        row.updated_at = now
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="quotation.void",
            entity_type="quotation",
            entity_id=row.id,
            document_number=row.document_number,
            before={"status": previous_status},
            after={"status": "void", "reason": reason},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return _response(session, row)


def clone_quotation(
    session: OrmSession,
    *,
    scope: OrganizationScope,
    quotation_id: UUID,
    quotation_date: date,
    request_id: UUID,
) -> QuotationResponse:
    source = session.scalar(
        scope.constrain(select(Quotation), model=Quotation).where(Quotation.id == quotation_id)
    )
    if source is None:
        raise QuotationNotFoundError
    payload = QuotationCreate(
        quotation_date=quotation_date,
        customer_id=source.customer_id,
        notes=source.notes,
        items=[
            QuotationItemResponse.model_validate(item, from_attributes=True).model_dump(
                exclude={"id", "line_number"}
            )
            for item in _items(session, source)
        ],
    )
    return create_quotation(
        session, scope=scope, payload=payload, request_id=request_id, source=source
    )
