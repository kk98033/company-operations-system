"""Response metadata contract shared by every paginated list endpoint."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.api.contracts.list_query import (
    MAX_PAGE,
    MAX_PAGE_SIZE,
    PageParams,
    SortDirection,
    SortField,
    SortParams,
)

ListItem = TypeVar("ListItem")
FilterSummary = TypeVar("FilterSummary", bound=BaseModel)


class PaginationMeta(BaseModel):
    """Counts and navigation state for one bounded result page."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(ge=1, le=MAX_PAGE)
    page_size: int = Field(ge=1, le=MAX_PAGE_SIZE)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_previous: bool
    has_next: bool

    @classmethod
    def from_total(
        cls,
        *,
        page: int,
        page_size: int,
        total_items: int,
    ) -> PaginationMeta:
        """Calculate stable pagination metadata without any database dependency."""

        if page < 1 or page_size < 1 or total_items < 0:
            raise ValueError("pagination values are outside their valid range")
        total_pages = (total_items + page_size - 1) // page_size
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_previous=page > 1 and total_items > 0,
            has_next=page < total_pages,
        )


class SortMeta(BaseModel):
    """Effective sorting echoed to the caller."""

    model_config = ConfigDict(frozen=True)

    field: str
    direction: SortDirection


class ListResponseMeta(BaseModel, Generic[FilterSummary]):
    """Complete metadata accompanying a list response."""

    model_config = ConfigDict(frozen=True)

    pagination: PaginationMeta
    sort: SortMeta
    filters: FilterSummary


class ListResponse(BaseModel, Generic[ListItem, FilterSummary]):
    """Generic top-level response for all bounded list endpoints."""

    items: list[ListItem]
    meta: ListResponseMeta[FilterSummary]


def build_list_response(
    *,
    items: Sequence[ListItem],
    total_items: int,
    page: PageParams,
    sort: SortParams[SortField],
    filters: FilterSummary,
) -> ListResponse[ListItem, FilterSummary]:
    """Build a list envelope from already-fetched items and a total count."""

    return ListResponse[ListItem, FilterSummary](
        items=list(items),
        meta=ListResponseMeta[FilterSummary](
            pagination=PaginationMeta.from_total(
                page=page.page,
                page_size=page.page_size,
                total_items=total_items,
            ),
            sort=SortMeta(
                field=sort.sort_by.value,
                direction=sort.sort_direction,
            ),
            filters=filters,
        ),
    )
