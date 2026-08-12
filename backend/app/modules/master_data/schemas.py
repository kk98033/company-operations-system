"""Master-data API contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.contracts import ListResponse, SortDirection


class MasterStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class VendorCategory(StrEnum):
    SUPPLIER = "supplier"
    COLLABORATOR = "collaborator"


class MasterSortField(StrEnum):
    CODE = "code"


class MasterSortParams(BaseModel):
    sort_by: MasterSortField = MasterSortField.CODE
    sort_direction: SortDirection = SortDirection.ASC


class MasterFilters(BaseModel):
    keyword: str | None
    status: MasterStatus | None


class VendorWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=100)
    category: VendorCategory
    contact_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    phone_secondary: str | None = Field(default=None, max_length=32)
    mobile: str | None = Field(default=None, max_length=32)
    fax: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    postal_code: str | None = Field(default=None, max_length=16)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    settlement_day: int | None = Field(default=None, ge=1, le=31)

    @field_validator(
        "short_name",
        "contact_name",
        "phone",
        "phone_secondary",
        "mobile",
        "fax",
        "email",
        "postal_code",
        "city",
        "address",
    )
    @classmethod
    def optional_blank_is_none(cls, value: str | None) -> str | None:
        return value or None


class VendorCreate(VendorWrite):
    pass


class VendorUpdate(VendorWrite):
    expected_updated_at: datetime


class VendorResponse(VendorWrite):
    id: UUID
    status: MasterStatus
    created_at: datetime
    updated_at: datetime


class VendorListResponse(ListResponse[VendorResponse, MasterFilters]):
    pass


class CatalogWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0, le=9999)


class CatalogCreate(CatalogWrite):
    pass


class CatalogUpdate(CatalogWrite):
    expected_updated_at: datetime


class CatalogResponse(CatalogWrite):
    id: UUID
    status: MasterStatus
    created_at: datetime
    updated_at: datetime


class CatalogListResponse(ListResponse[CatalogResponse, MasterFilters]):
    pass


class ProcessDefinitionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    sort_order: int
    is_system: bool
    status: MasterStatus
    created_at: datetime
    updated_at: datetime


class ProcessDefinitionListResponse(ListResponse[ProcessDefinitionResponse, MasterFilters]):
    pass


class MasterStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: datetime
    status: MasterStatus
