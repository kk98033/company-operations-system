"""Statements, receipts, and receivable aging API."""

from datetime import date
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database.session import get_database_session
from app.core.errors import ApplicationError
from app.core.request_context import require_request_id
from app.modules.auth.dependencies import require_authenticated_csrf
from app.modules.auth.services import AuthenticatedSession
from app.modules.authorization.dependencies import require_capability
from app.modules.billing.errors import BillingConflictError, BillingNotFoundError, BillingStateError
from app.modules.billing.query_service import (
    get_receipt,
    get_statement,
    list_aging,
    list_pending_statement_items,
    list_receipts,
    list_statements,
)
from app.modules.billing.receipt_service import create_receipt, reverse_receipt
from app.modules.billing.schemas import (
    AgingSummary,
    PendingStatementListResponse,
    ReceiptCreate,
    ReceiptListResponse,
    ReceiptResponse,
    ReceiptReverse,
    StatementCancel,
    StatementCommand,
    StatementCreate,
    StatementListResponse,
    StatementResponse,
)
from app.modules.billing.statement_service import (
    cancel_statement,
    create_statement,
    issue_statement,
)
from app.modules.organizations.scope import OrganizationScope

_statement_read = require_capability("statement.read")
_statement_issue = require_capability("statement.issue")
_statement_cancel = require_capability("statement.cancel")
_receipt_read = require_capability("receipt.read")
_receipt_record = require_capability("receipt.record")
_receipt_reverse = require_capability("receipt.reverse")
ERRORS = (BillingNotFoundError, BillingConflictError, BillingStateError)


def _scope(context: AuthenticatedSession) -> OrganizationScope:
    return OrganizationScope(
        organization_id=context.organization_id,
        organization_member_id=context.organization_member_id,
        actor_user_id=context.user_id,
    )


def _translate(error: Exception) -> NoReturn:
    if isinstance(error, BillingNotFoundError):
        raise ApplicationError(
            status_code=404, code="BILLING_NOT_FOUND", message="找不到帳務資料"
        ) from None
    if isinstance(error, BillingStateError):
        raise ApplicationError(
            status_code=409, code="BILLING_STATE_CONFLICT", message="目前狀態不允許此操作"
        ) from None
    raise ApplicationError(
        status_code=409, code="BILLING_UPDATE_CONFLICT", message="來源重複、金額超額或資料已變更"
    ) from None


def build_billing_router() -> APIRouter:
    router = APIRouter(tags=["billing"])

    @router.get(
        "/statements/pending-items",
        response_model=PendingStatementListResponse,
        operation_id="statement_pending_item_list",
    )
    def pending(
        context: Annotated[AuthenticatedSession, Depends(_statement_read)],
        session: Annotated[Session, Depends(get_database_session)],
        keyword: Annotated[str | None, Query(max_length=200)] = None,
    ):
        items = list_pending_statement_items(session, _scope(context), keyword)
        return PendingStatementListResponse(items=items, total_items=len(items))

    @router.get("/statements", response_model=StatementListResponse, operation_id="statement_list")
    def statements(
        context: Annotated[AuthenticatedSession, Depends(_statement_read)],
        session: Annotated[Session, Depends(get_database_session)],
        keyword: Annotated[str | None, Query(max_length=200)] = None,
        status: Annotated[str | None, Query()] = None,
    ):
        items = list_statements(session, _scope(context), keyword, status)
        return StatementListResponse(items=items, total_items=len(items))

    @router.post(
        "/statements",
        response_model=StatementResponse,
        status_code=201,
        operation_id="statement_create",
    )
    def create(
        payload: StatementCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_statement_issue)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return create_statement(
                session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get(
        "/statements/{statement_id}", response_model=StatementResponse, operation_id="statement_get"
    )
    def detail(
        statement_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_statement_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return get_statement(session, _scope(context), statement_id)
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/statements/{statement_id}/issue",
        response_model=StatementResponse,
        operation_id="statement_issue",
    )
    def issue(
        statement_id: UUID,
        payload: StatementCommand,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_statement_issue)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return issue_statement(
                session,
                scope=_scope(context),
                statement_id=statement_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/statements/{statement_id}/cancel",
        response_model=StatementResponse,
        operation_id="statement_cancel",
    )
    def cancel(
        statement_id: UUID,
        payload: StatementCancel,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_statement_cancel)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return cancel_statement(
                session,
                scope=_scope(context),
                statement_id=statement_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get("/receipts", response_model=ReceiptListResponse, operation_id="receipt_list")
    def receipts(
        context: Annotated[AuthenticatedSession, Depends(_receipt_read)],
        session: Annotated[Session, Depends(get_database_session)],
        keyword: Annotated[str | None, Query(max_length=200)] = None,
    ):
        items = list_receipts(session, _scope(context), keyword)
        return ReceiptListResponse(items=items, total_items=len(items))

    @router.post(
        "/receipts", response_model=ReceiptResponse, status_code=201, operation_id="receipt_create"
    )
    def receipt_create(
        payload: ReceiptCreate,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_receipt_record)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return create_receipt(
                session,
                scope=_scope(context),
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get(
        "/receipts/{receipt_id}", response_model=ReceiptResponse, operation_id="receipt_get"
    )
    def receipt_get(
        receipt_id: UUID,
        context: Annotated[AuthenticatedSession, Depends(_receipt_read)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return get_receipt(session, _scope(context), receipt_id)
        except ERRORS as error:
            _translate(error)

    @router.post(
        "/receipts/{receipt_id}/reverse",
        response_model=ReceiptResponse,
        operation_id="receipt_reverse",
    )
    def reverse(
        receipt_id: UUID,
        payload: ReceiptReverse,
        request: Request,
        context: Annotated[AuthenticatedSession, Depends(_receipt_reverse)],
        _csrf: Annotated[None, Depends(require_authenticated_csrf)],
        session: Annotated[Session, Depends(get_database_session)],
    ):
        try:
            return reverse_receipt(
                session,
                scope=_scope(context),
                receipt_id=receipt_id,
                payload=payload,
                request_id=require_request_id(request),
            )
        except ERRORS as error:
            _translate(error)

    @router.get(
        "/receivables/aging",
        response_model=list[AgingSummary],
        operation_id="receivable_aging_list",
    )
    def aging(
        context: Annotated[AuthenticatedSession, Depends(_receipt_read)],
        session: Annotated[Session, Depends(get_database_session)],
        as_of: Annotated[date, Query()],
    ):
        return list_aging(session, _scope(context), as_of)

    return router
