"""Typed statement and receipt API contracts."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StatementStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


class StatementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    statement_date: date
    period_from: date
    period_to: date
    pricing_item_ids: list[UUID] = Field(min_length=1, max_length=500)
    tax_enabled: bool = False
    tax_rate_percent: Decimal | None = Field(default=None, gt=0, le=100, decimal_places=4)
    rounding_scope: str | None = None
    rounding_decimal_places: int | None = Field(default=None, ge=0, le=4)
    notes: str | None = Field(default=None, max_length=2000)
    idempotency_key: UUID

    @model_validator(mode="after")
    def validate_policy(self) -> "StatementCreate":
        if self.period_from > self.period_to:
            raise ValueError("statement period is invalid")
        conditional = (self.tax_rate_percent, self.rounding_scope, self.rounding_decimal_places)
        if self.tax_enabled and (
            any(value is None for value in conditional)
            or self.rounding_scope not in {"per_line", "grand_total"}
        ):
            raise ValueError("enabled tax requires rate and rounding policy")
        if not self.tax_enabled and any(value is not None for value in conditional):
            raise ValueError("disabled tax cannot carry tax policy")
        return self


class StatementCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(gt=0)
    idempotency_key: UUID


class StatementCancel(StatementCommand):
    reason: str = Field(min_length=1, max_length=1000)


class StatementItemResponse(BaseModel):
    id: UUID
    source_pricing_item_id: UUID
    source_pricing_document_id: UUID
    line_no: int
    content: str
    quantity: Decimal
    unit_price: Decimal
    plate_fee: Decimal
    die_fee: Decimal
    amount: Decimal
    source_snapshot: dict


class StatementResponse(BaseModel):
    id: UUID
    document_number: str
    statement_date: date
    period_from: date
    period_to: date
    customer_id: UUID
    customer_name: str
    status: StatementStatus
    version: int
    tax_enabled: bool
    tax_rate_percent: Decimal | None
    rounding_scope: str | None
    rounding_decimal_places: int | None
    subtotal_before_rounding: Decimal
    rounding_adjustment: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    notes: str | None
    items: list[StatementItemResponse]
    issued_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime


class StatementSummary(BaseModel):
    id: UUID
    document_number: str
    statement_date: date
    customer_id: UUID
    customer_name: str
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: StatementStatus


class PendingStatementItem(BaseModel):
    pricing_item_id: UUID
    pricing_document_id: UUID
    pricing_document_number: str
    pricing_date: date
    customer_id: UUID
    customer_name: str
    content: str
    amount: Decimal


class StatementListResponse(BaseModel):
    items: list[StatementSummary]
    total_items: int


class PendingStatementListResponse(BaseModel):
    items: list[PendingStatementItem]
    total_items: int


class ReceiptAllocationInput(BaseModel):
    statement_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=4)


class ReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    receipt_date: date
    customer_id: UUID
    payment_method: str = Field(min_length=1, max_length=64)
    reference_number: str | None = Field(default=None, max_length=128)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    allocations: list[ReceiptAllocationInput] = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    idempotency_key: UUID


class ReceiptReverse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    idempotency_key: UUID
    reason: str = Field(min_length=1, max_length=1000)


class ReceiptAllocationResponse(BaseModel):
    statement_id: UUID
    statement_number: str
    amount: Decimal


class ReceiptResponse(BaseModel):
    id: UUID
    document_number: str
    receipt_date: date
    customer_id: UUID
    customer_name: str
    payment_method: str
    reference_number: str | None
    amount: Decimal
    status: str
    allocations: list[ReceiptAllocationResponse]
    notes: str | None
    confirmed_at: datetime
    reversed_at: datetime | None
    reversal_reason: str | None


class ReceiptListResponse(BaseModel):
    items: list[ReceiptResponse]
    total_items: int


class AgingSummary(BaseModel):
    customer_id: UUID
    customer_name: str
    current_amount: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_over_90: Decimal
    total_outstanding: Decimal
