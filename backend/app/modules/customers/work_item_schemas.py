"""Customer work-item API contracts."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.contracts import ListResponse, SortDirection, SortParams
from app.modules.customers.schemas import CustomerStatus


class WorkItemSource(StrEnum):
    MANUAL = "manual"
    LEGACY = "legacy"
    WORK_ORDER = "work_order"


class WorkItemSortField(StrEnum):
    NAME = "name"


class WorkItemSortParams(SortParams[WorkItemSortField]):
    sort_by: WorkItemSortField = WorkItemSortField.NAME
    sort_direction: SortDirection = SortDirection.ASC


class WorkItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    specification: str | None = Field(default=None, max_length=4000)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=4)

    @field_validator("specification")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        return value or None


class WorkItemCreate(WorkItemWrite):
    pass


class WorkItemUpdate(WorkItemWrite):
    expected_updated_at: datetime


class WorkItemResponse(WorkItemWrite):
    id: UUID
    customer_id: UUID
    source: WorkItemSource
    source_reference: str | None
    legacy_source_table: str | None
    legacy_source_key: str | None
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime


class WorkItemFilters(BaseModel):
    keyword: str | None
    status: CustomerStatus | None


class WorkItemListResponse(ListResponse[WorkItemResponse, WorkItemFilters]):
    pass


class WorkItemStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: datetime
    status: CustomerStatus
