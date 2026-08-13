"""Atomic, idempotent quotation-item to case/work-order conversion."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit import record_user_audit_event
from app.modules.organizations.scope import OrganizationScope
from app.modules.quotations.models import Quotation, QuotationItem
from app.modules.work_orders.case_service import case_response, create_case_row
from app.modules.work_orders.errors import (
    QuotationConversionError,
    WorkOrderConflictError,
    WorkOrderNotFoundError,
)
from app.modules.work_orders.models import ProductionCase, WorkOrder
from app.modules.work_orders.schemas import (
    PROCESS_CODES,
    PROCESS_NAMES,
    CaseCreate,
    CaseResponse,
    QuotationConversionRequest,
    WorkOrderCreate,
)
from app.modules.work_orders.service import create_work_order_row


def _empty_processes() -> list[dict]:
    return [
        {"code": code, "name": name}
        for code, name in zip(PROCESS_CODES, PROCESS_NAMES, strict=True)
    ]


def _payload(*, quotation: Quotation, item: QuotationItem, order_date: date) -> WorkOrderCreate:
    processes = _empty_processes()
    for process in processes:
        if process["code"] == "coating" and item.coating:
            process["coating_type"] = item.coating
    return WorkOrderCreate(
        case_id=None,
        order_date=order_date,
        delivery_date=None,
        customer_id=quotation.customer_id,
        customer_order_number=None,
        product_name=item.product_name,
        order_quantity=item.quantity,
        specification=item.note,
        unit_price=item.unit_price,
        plate_fee=item.plate_fee,
        die_fee=item.die_fee,
        papers=[
            {"type": "face", "paper": item.paper, "size": item.size},
            {"type": "back"},
            {"type": "flute"},
        ],
        print_specification={
            "front": {"special_colors": item.color},
            "back": {},
        },
        processes=processes,
        notes=quotation.notes,
    )


def convert_quotation(
    session: Session,
    *,
    scope: OrganizationScope,
    payload: QuotationConversionRequest,
    request_id: UUID,
) -> CaseResponse:
    try:
        existing = session.scalar(
            scope.constrain(select(ProductionCase), model=ProductionCase).where(
                ProductionCase.source_quotation_id == payload.quotation_id
            )
        )
        requested_ids = set(payload.item_ids)
        if len(requested_ids) != len(payload.item_ids):
            raise QuotationConversionError
        if existing is not None:
            converted_ids = set(
                session.scalars(
                    select(WorkOrder.source_quotation_item_id).where(
                        WorkOrder.organization_id == scope.organization_id,
                        WorkOrder.case_id == existing.id,
                    )
                ).all()
            )
            if converted_ids != requested_ids:
                raise WorkOrderConflictError
            return case_response(session, existing)
        quotation = session.scalar(
            scope.constrain(select(Quotation), model=Quotation)
            .where(Quotation.id == payload.quotation_id)
            .with_for_update()
        )
        if quotation is None:
            raise WorkOrderNotFoundError
        if quotation.status != "confirmed":
            raise QuotationConversionError
        items = list(
            session.scalars(
                select(QuotationItem)
                .where(
                    QuotationItem.organization_id == scope.organization_id,
                    QuotationItem.quotation_id == quotation.id,
                    QuotationItem.id.in_(requested_ids),
                )
                .order_by(QuotationItem.line_number)
            ).all()
        )
        if {item.id for item in items} != requested_ids:
            raise QuotationConversionError
        parent = create_case_row(
            session,
            scope=scope,
            payload=CaseCreate(
                case_date=quotation.quotation_date,
                customer_id=quotation.customer_id,
                notes=quotation.notes,
            ),
            source_quotation_id=quotation.id,
        )
        orders = [
            create_work_order_row(
                session,
                scope=scope,
                payload=_payload(
                    quotation=quotation,
                    item=item,
                    order_date=quotation.quotation_date,
                ),
                case=parent,
                source_quotation_item_id=item.id,
            )
            for item in items
        ]
        record_user_audit_event(
            session,
            scope=scope,
            request_id=request_id,
            action="quotation.convert_to_case",
            entity_type="production_case",
            entity_id=parent.id,
            document_number=parent.case_number,
            before={"quotation_id": str(quotation.id)},
            after={"work_order_ids": [str(item.id) for item in orders]},
        )
        session.commit()
    except (WorkOrderNotFoundError, WorkOrderConflictError, QuotationConversionError):
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise WorkOrderConflictError from None
    return case_response(session, parent)
