"""Customer API contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.contracts import ListResponse, SortDirection


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomerSortField(StrEnum):
    CODE = "code"
    NAME = "name"
    UPDATED_AT = "updated_at"


class CustomerFilterSummary(BaseModel):
    keyword: str | None
    status: CustomerStatus | None


class CustomerResponse(BaseModel):
    id: UUID
    code: str
    name: str
    short_name: str | None
    tax_identifier: str | None
    contact_name: str | None
    phone: str | None
    phone_secondary: str | None
    mobile: str | None
    fax: str | None
    email: str | None
    postal_code: str | None
    city: str | None
    address: str | None
    payment_terms: str | None
    legacy_tax_setting_raw: str | None
    legacy_rounding_setting_raw: str | None
    legacy_source_table: str | None
    legacy_source_key: str | None
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(ListResponse[CustomerResponse, CustomerFilterSummary]):
    pass


class CustomerWriteBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=100)
    tax_identifier: str | None = Field(default=None, max_length=20)
    contact_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    phone_secondary: str | None = Field(default=None, max_length=32)
    mobile: str | None = Field(default=None, max_length=32)
    fax: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    postal_code: str | None = Field(default=None, max_length=16)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    payment_terms: str | None = Field(default=None, max_length=200)

    @field_validator(
        "short_name", "tax_identifier", "contact_name", "phone", "phone_secondary",
        "mobile", "fax", "email", "postal_code", "city", "address", "payment_terms",
    )
    @classmethod
    def empty_optional_is_none(cls, value: str | None) -> str | None:
        return value or None


class CustomerCreate(CustomerWriteBase):
    pass


class CustomerUpdate(CustomerWriteBase):
    expected_updated_at: datetime


class CustomerStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: datetime
    status: CustomerStatus


class CustomerSortParams(BaseModel):
    sort_by: CustomerSortField = CustomerSortField.CODE
    sort_direction: SortDirection = SortDirection.ASC
