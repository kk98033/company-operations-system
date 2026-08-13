"""Shipment API contracts."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.contracts import ListResponse, SortDirection, SortParams


class ShipmentStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ShipmentItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_order_id: UUID
    delivered_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    spare_quantity: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=4)

    @model_validator(mode="after")
    def require_quantity(self) -> "ShipmentItemInput":
        if self.delivered_quantity + self.spare_quantity <= 0:
            raise ValueError("正式出貨量與備品量合計必須大於零")
        return self


class ShipmentDraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    shipment_date: date
    customer_id: UUID
    delivery_address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    items: list[ShipmentItemInput] = Field(min_length=1, max_length=100)
    idempotency_key: UUID


class ShipmentDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    shipment_date: date
    delivery_address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)
    items: list[ShipmentItemInput] = Field(min_length=1, max_length=100)
    expected_version: int = Field(gt=0)


class CompletionDuringShipment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    work_order_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    reason: str = Field(min_length=1, max_length=1000)


class ShipmentConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(gt=0)
    idempotency_key: UUID
    completions: list[CompletionDuringShipment] = Field(default_factory=list, max_length=100)


class ShipmentCancel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(gt=0)
    idempotency_key: UUID
    reason: str = Field(min_length=1, max_length=1000)


class AvailableShipmentItem(BaseModel):
    work_order_id: UUID
    document_number: str
    customer_id: UUID
    customer_name: str
    customer_order_number: str | None
    product_name: str
    specification: str | None
    order_quantity: Decimal
    available_quantity: Decimal


class ShipmentItemResponse(BaseModel):
    id: UUID
    work_order_id: UUID
    line_no: int
    work_order_document_number: str
    customer_order_number: str | None
    product_name: str
    specification: str | None
    delivered_quantity: Decimal
    spare_quantity: Decimal
    inventory_consumed_quantity: Decimal
    available_quantity_snapshot: Decimal | None
    cumulative_delivered_snapshot: Decimal | None


class ShipmentResponse(BaseModel):
    id: UUID
    document_number: str
    shipment_date: date
    customer_id: UUID
    customer_name: str
    delivery_address: str | None
    notes: str | None
    status: ShipmentStatus
    version: int
    legacy_document_number: str | None
    items: list[ShipmentItemResponse]
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime
    warnings: list[str] = Field(default_factory=list)


class ShipmentSummary(BaseModel):
    id: UUID
    document_number: str
    legacy_document_number: str | None
    shipment_date: date
    customer_name: str
    status: ShipmentStatus
    line_count: int
    delivered_quantity: Decimal
    spare_quantity: Decimal
    created_at: datetime


class ShipmentFilters(BaseModel):
    keyword: str | None
    status: ShipmentStatus | None


class ShipmentSortField(StrEnum):
    SHIPMENT_DATE = "shipment_date"


class ShipmentSortParams(SortParams[ShipmentSortField]):
    sort_by: ShipmentSortField = ShipmentSortField.SHIPMENT_DATE
    sort_direction: SortDirection = SortDirection.DESC


class ShipmentListResponse(ListResponse[ShipmentSummary, ShipmentFilters]):
    pass


class AvailableShipmentListResponse(ListResponse[AvailableShipmentItem, ShipmentFilters]):
    pass
