"""Typed production, final completion, and inventory API contracts."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.contracts import ListResponse, SortDirection, SortParams
from app.modules.work_orders.schemas import PROCESS_CODES, PROCESS_NAMES


class ProcessCode(StrEnum):
    ARTWORK = "artwork"
    OUTPUT = "output"
    PLATE = "plate"
    PROOF = "proof"
    PRINTING = "printing"
    COATING = "coating"
    MOUNTING = "mounting"
    DIE = "die"
    DIE_CUTTING = "die_cutting"
    FINISHING = "finishing"
    GLUING = "gluing"
    TRANSPORT = "transport"
    OTHER = "other"


class ProcessEventType(StrEnum):
    START = "start"
    PARTIAL_COMPLETE = "partial_complete"
    COMPLETE = "complete"
    REOPEN = "reopen"


class ProcessState(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"
    COMPLETED = "completed"


class ProcessEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    process_code: ProcessCode
    event_type: ProcessEventType
    completed_quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)
    reason: str | None = Field(default=None, max_length=1000)
    idempotency_key: UUID

    @model_validator(mode="after")
    def validate_shape(self) -> "ProcessEventCreate":
        if (self.event_type == ProcessEventType.PARTIAL_COMPLETE) != (
            self.completed_quantity is not None
        ):
            raise ValueError("部分完成必須填寫本次完成量，其他事件不可填")
        if self.event_type == ProcessEventType.REOPEN and not self.reason:
            raise ValueError("重開製程必須填寫原因")
        return self


class ProcessEventResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    process_code: ProcessCode
    process_name: str
    event_type: ProcessEventType
    sequence_no: int
    completed_quantity: Decimal | None
    reason: str | None
    occurred_at: datetime
    created_at: datetime


class ProcessStateResponse(BaseModel):
    code: ProcessCode
    name: str
    state: ProcessState
    latest_event: ProcessEventResponse | None


class FinalCompletionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: UUID


class ReversalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: UUID


class InventoryAdjustmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    quantity: Decimal = Field(max_digits=14, decimal_places=4)
    reason: str = Field(min_length=1, max_length=1000)
    idempotency_key: UUID

    @model_validator(mode="after")
    def nonzero(self) -> "InventoryAdjustmentCreate":
        if self.quantity == 0:
            raise ValueError("調整量不可為零")
        return self


class FinalCompletionResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    entry_type: str
    source_type: str
    quantity: Decimal
    transport_process_event_id: UUID | None
    reversal_of_id: UUID | None
    correlation_id: UUID
    reason: str
    occurred_at: datetime
    created_at: datetime
    available_quantity: Decimal
    exceeds_order_quantity: bool


class InventoryLedgerResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    event_type: str
    quantity: Decimal
    reason: str
    final_completion_entry_id: UUID | None
    inventory_adjustment_id: UUID | None
    occurred_at: datetime
    created_at: datetime


class ProductionOrderSummary(BaseModel):
    work_order_id: UUID
    document_number: str
    customer_name: str
    product_name: str
    order_quantity: Decimal
    delivery_date: date | None
    process_completed_count: int
    transport_state: ProcessState
    available_quantity: Decimal


class ProductionFilters(BaseModel):
    keyword: str | None


class ProductionSortField(StrEnum):
    DELIVERY_DATE = "delivery_date"


class ProductionSortParams(SortParams[ProductionSortField]):
    sort_by: ProductionSortField = ProductionSortField.DELIVERY_DATE
    sort_direction: SortDirection = SortDirection.ASC


class ProductionOrderListResponse(ListResponse[ProductionOrderSummary, ProductionFilters]):
    pass


class ProductionOrderDetail(BaseModel):
    order: ProductionOrderSummary
    processes: list[ProcessStateResponse]
    final_completions: list[FinalCompletionResponse]
    ledger: list[InventoryLedgerResponse]


class InventoryPosition(BaseModel):
    work_order_id: UUID
    document_number: str
    customer_name: str
    product_name: str
    order_quantity: Decimal
    available_quantity: Decimal
    delivery_date: date | None


class InventoryFilters(BaseModel):
    keyword: str | None
    positive_only: bool


class InventorySortField(StrEnum):
    DOCUMENT_NUMBER = "document_number"


class InventorySortParams(SortParams[InventorySortField]):
    sort_by: InventorySortField = InventorySortField.DOCUMENT_NUMBER
    sort_direction: SortDirection = SortDirection.ASC


class InventoryListResponse(ListResponse[InventoryPosition, InventoryFilters]):
    pass


PROCESS_NAME_BY_CODE = dict(zip(PROCESS_CODES, PROCESS_NAMES, strict=True))
