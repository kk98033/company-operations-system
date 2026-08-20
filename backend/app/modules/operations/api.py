"""HTTP endpoints for Phase 9 cross-module operations."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.audit import record_user_audit_event
from app.modules.auth.dependencies import require_current_session
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.capabilities import has_capability
from app.modules.authorization.security import persist_permission_denial
from app.modules.billing.models import Statement
from app.modules.customers.models import Customer
from app.modules.operations.common import build_operations_context
from app.modules.operations.csv_export import render_csv
from app.modules.operations.customer_360 import (
    CustomerOverviewNotFoundError,
    load_customer_overview,
)
from app.modules.operations.dashboard import load_dashboard
from app.modules.operations.schemas import (
    CustomerOverviewResponse,
    DashboardResponse,
    SearchResponse,
)
from app.modules.operations.search import global_search
from app.modules.shipments.models import Shipment
from app.modules.work_orders.models import WorkOrder

ExportDataset = Literal["customers", "work-orders", "shipments", "statements"]
_EXPORTS = {
    "customers": (
        "customers.read",
        Customer,
        ["客戶代號", "客戶名稱", "聯絡人", "電話", "Email", "狀態"],
        lambda r: (r.code, r.name, r.contact_name, r.phone, r.email, r.status),
    ),
    "work-orders": (
        "work_orders.read",
        WorkOrder,
        ["工單號碼", "舊單號", "日期", "交期", "客戶", "品名", "數量", "狀態"],
        lambda r: (
            r.document_number,
            r.legacy_document_number,
            r.order_date,
            r.delivery_date,
            r.customer_snapshot.get("name", ""),
            r.product_name,
            r.order_quantity,
            r.status,
        ),
    ),
    "shipments": (
        "shipment.read",
        Shipment,
        ["出貨單號", "舊單號", "日期", "客戶", "狀態"],
        lambda r: (
            r.document_number,
            r.legacy_document_number,
            r.shipment_date,
            r.customer_snapshot.get("name", ""),
            r.status,
        ),
    ),
    "statements": (
        "statement.read",
        Statement,
        ["對帳單號", "日期", "客戶", "未稅金額", "稅額", "總額", "狀態"],
        lambda r: (
            r.document_number,
            r.statement_date,
            r.customer_snapshot.get("name", ""),
            r.subtotal,
            r.tax_amount,
            r.grand_total,
            r.status,
        ),
    ),
}


def build_operations_router() -> APIRouter:
    router = APIRouter(prefix="/operations", tags=["operations"])

    @router.get("/dashboard", response_model=DashboardResponse, operation_id="operations_dashboard")
    def dashboard(
        identity: Annotated[AuthenticatedSession, Depends(require_current_session)],
        db: Annotated[Session, Depends(get_database_session)],
        as_of: Annotated[date | None, Query()] = None,
    ) -> DashboardResponse:
        return load_dashboard(
            db,
            context=build_operations_context(db, identity),
            as_of=as_of or date.today(),
        )

    @router.get("/search", response_model=SearchResponse, operation_id="operations_search")
    def search(
        identity: Annotated[AuthenticatedSession, Depends(require_current_session)],
        db: Annotated[Session, Depends(get_database_session)],
        keyword: Annotated[str, Query(min_length=2, max_length=100)],
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> SearchResponse:
        return global_search(
            db, context=build_operations_context(db, identity), keyword=keyword.strip(), limit=limit
        )

    @router.get(
        "/customers/{customer_id}",
        response_model=CustomerOverviewResponse,
        operation_id="operations_customer_overview",
    )
    def customer_overview(
        customer_id: UUID,
        request: Request,
        identity: Annotated[AuthenticatedSession, Depends(require_current_session)],
        db: Annotated[Session, Depends(get_database_session)],
    ) -> CustomerOverviewResponse:
        context = build_operations_context(db, identity)
        if not context.can("customers.read"):
            persist_permission_denial(
                db,
                context=identity,
                request_id=require_request_id(request),
                capability="customers.read",
            )
            raise ApplicationError(
                status_code=403, code="PERMISSION_DENIED", message="沒有執行此操作的權限"
            )
        try:
            return load_customer_overview(db, context=context, customer_id=customer_id)
        except CustomerOverviewNotFoundError:
            raise ApplicationError(
                status_code=404, code="CUSTOMER_NOT_FOUND", message="找不到客戶資料"
            ) from None

    @router.get(
        "/exports/{dataset}.csv", operation_id="operations_export_csv", response_class=Response
    )
    def export_csv(
        dataset: ExportDataset,
        request: Request,
        identity: Annotated[AuthenticatedSession, Depends(require_current_session)],
        db: Annotated[Session, Depends(get_database_session)],
    ) -> Response:
        capability, model, headers, mapper = _EXPORTS[dataset]
        if not has_capability(
            db,
            organization_member_id=identity.organization_member_id,
            organization_id=identity.organization_id,
            capability=capability,
        ):
            persist_permission_denial(
                db,
                context=identity,
                request_id=require_request_id(request),
                capability=capability,
            )
            raise ApplicationError(
                status_code=403, code="PERMISSION_DENIED", message="沒有執行此操作的權限"
            )
        total = (
            db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.organization_id == identity.organization_id)
            )
            or 0
        )
        if total > 10000:
            raise ApplicationError(
                status_code=409,
                code="EXPORT_LIMIT_EXCEEDED",
                message="資料超過一萬筆，請改用篩選後匯出",
            )
        rows = db.scalars(
            select(model)
            .where(model.organization_id == identity.organization_id)
            .order_by(model.created_at.desc())
            .limit(10000)
        ).all()
        content = render_csv(headers, (mapper(row) for row in rows))
        record_user_audit_event(
            db,
            scope=build_operations_context(db, identity).scope,
            request_id=require_request_id(request),
            action="operations.csv_export",
            entity_type="data_export",
            after={"dataset": dataset, "row_count": len(rows)},
        )
        db.commit()
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{dataset}.csv"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    return router
