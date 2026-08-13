"""Typed pricing API contracts."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.contracts import ListResponse, SortDirection, SortParams


class PricingStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PendingPricingStatus(StrEnum):
    PENDING = "pending"
    PRICING = "pricing"
    PRICED = "priced"
    CANCELLED = "cancelled"


class PricingItemType(StrEnum):
    BASE = "base"
    SPARE = "spare"
    MANUAL = "manual"


class PricingDraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pricing_date: date
    shipment_item_ids: list[UUID] = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    idempotency_key: UUID


class PricingItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_shipment_item_id: UUID | None = None
    item_type: PricingItemType
    content: str = Field(min_length=1, max_length=500)
    product_name: str | None = Field(default=None, max_length=500)
    specification: str | None = Field(default=None, max_length=2000)
    quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    plate_fee: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=4)
    die_fee: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=4)

    @model_validator(mode="after")
    def validate_source(self) -> "PricingItemInput":
        if self.item_type == PricingItemType.MANUAL and self.source_shipment_item_id is not None:
            raise ValueError("手動明細不得偽裝成出貨來源")
        if self.item_type != PricingItemType.MANUAL and self.source_shipment_item_id is None:
            raise ValueError("基礎或備品明細必須保留出貨來源")
        return self


class PricingDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pricing_date: date
    notes: str | None = Field(default=None, max_length=2000)
    items: list[PricingItemInput] = Field(min_length=1, max_length=200)
    expected_version: int = Field(gt=0)


class PricingConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(gt=0)
    idempotency_key: UUID
    update_default_line_numbers: list[int] = Field(default_factory=list, max_length=200)


class PricingCancel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(gt=0)
    idempotency_key: UUID
    reason: str = Field(min_length=1, max_length=1000)


class PricingReopen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(gt=0)
    idempotency_key: UUID


class PricingItemResponse(BaseModel):
    id: UUID
    source_shipment_item_id: UUID | None
    line_no: int
    item_type: PricingItemType
    content: str
    product_name: str | None
    specification: str | None
    quantity: Decimal
    unit_price: Decimal
    plate_fee: Decimal
    die_fee: Decimal
    subtotal: Decimal
    source_snapshot: dict | None


class PricingResponse(BaseModel):
    id: UUID
    document_number: str
    pricing_date: date
    customer_id: UUID
    customer_name: str
    notes: str | None
    status: PricingStatus
    version: int
    legacy_document_number: str | None
    items: list[PricingItemResponse]
    total_amount: Decimal
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime


class PricingSummary(BaseModel):
    id: UUID
    document_number: str
    legacy_document_number: str | None
    pricing_date: date
    customer_name: str
    status: PricingStatus
    line_count: int
    total_amount: Decimal


class PendingPricingItem(BaseModel):
    shipment_item_id: UUID
    shipment_id: UUID
    shipment_document_number: str
    shipment_date: date
    customer_id: UUID
    customer_name: str
    work_order_document_number: str
    product_name: str
    specification: str | None
    delivered_quantity: Decimal
    spare_quantity: Decimal
    suggested_unit_price: Decimal
    pricing_status: PendingPricingStatus
    pricing_document_id: UUID | None
    pricing_document_number: str | None


class PriceSuggestion(BaseModel):
    id: UUID
    content: str
    product_name: str
    specification: str | None
    unit_price: Decimal
    plate_fee: Decimal
    die_fee: Decimal
    price_date: date
    source_pricing_item_id: UUID
    is_default: bool


class PricingFilters(BaseModel):
    keyword: str | None
    status: PricingStatus | None


class PendingPricingFilters(BaseModel):
    keyword: str | None
    status: PendingPricingStatus | None


class PricingSortField(StrEnum):
    PRICING_DATE = "pricing_date"


class PricingSortParams(SortParams[PricingSortField]):
    sort_by: PricingSortField = PricingSortField.PRICING_DATE
    sort_direction: SortDirection = SortDirection.DESC


class PricingListResponse(ListResponse[PricingSummary, PricingFilters]):
    pass


class PendingPricingListResponse(ListResponse[PendingPricingItem, PendingPricingFilters]):
    pass


class PriceSuggestionListResponse(BaseModel):
    items: list[PriceSuggestion]
