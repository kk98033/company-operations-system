"""Quotation API contracts."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.contracts import ListResponse, SortDirection, SortParams


class QuotationStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    VOID = "void"


class QuotationItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_name: str = Field(min_length=1, max_length=200)
    size: str | None = Field(default=None, max_length=200)
    paper: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, max_length=100)
    coating: str | None = Field(default=None, max_length=100)
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    plate_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    die_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=4)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("size", "paper", "color", "coating", "note")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        return value or None


class QuotationItemResponse(QuotationItemWrite):
    id: UUID
    line_number: int


class QuotationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    quotation_date: date
    customer_id: UUID
    notes: str | None = Field(default=None, max_length=4000)
    items: list[QuotationItemWrite] = Field(min_length=1, max_length=50)

    @field_validator("notes")
    @classmethod
    def blank_notes_is_none(cls, value: str | None) -> str | None:
        return value or None


class QuotationCreate(QuotationWrite):
    pass


class QuotationUpdate(QuotationWrite):
    expected_updated_at: datetime


class QuotationClone(BaseModel):
    quotation_date: date


class QuotationVoid(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_updated_at: datetime
    reason: str = Field(min_length=1, max_length=1000)


class QuotationResponse(BaseModel):
    id: UUID
    document_number: str
    quotation_date: date
    customer_id: UUID
    organization_snapshot: dict
    customer_snapshot: dict
    notes: str | None
    status: QuotationStatus
    source_quotation_id: UUID | None
    legacy_document_number: str | None
    legacy_tax_included_raw: str | None
    legacy_source_table: str | None
    legacy_source_key: str | None
    document_snapshot: dict | None
    print_metadata: dict | None
    confirmed_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[QuotationItemResponse]


class QuotationSummary(BaseModel):
    id: UUID
    document_number: str
    legacy_document_number: str | None
    quotation_date: date
    customer_name: str
    first_product_name: str
    item_count: int
    status: QuotationStatus
    updated_at: datetime


class QuotationFilters(BaseModel):
    keyword: str | None
    status: QuotationStatus | None
    date_from: date | None
    date_to: date | None


class QuotationSortField(StrEnum):
    DATE = "quotation_date"


class QuotationSortParams(SortParams[QuotationSortField]):
    sort_by: QuotationSortField = QuotationSortField.DATE
    sort_direction: SortDirection = SortDirection.DESC


class QuotationListResponse(ListResponse[QuotationSummary, QuotationFilters]):
    pass
