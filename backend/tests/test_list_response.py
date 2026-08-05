from enum import StrEnum

import pytest
from pydantic import BaseModel, ValidationError

from app.api.contracts import (
    PageParams,
    PaginationMeta,
    SortDirection,
    SortParams,
    build_list_response,
)


class ExampleItem(BaseModel):
    id: int


class ExampleFilters(BaseModel):
    keyword: str | None


class ExampleSortField(StrEnum):
    CREATED_AT = "created_at"


@pytest.mark.parametrize(
    ("page", "page_size", "total", "total_pages", "previous", "next_page"),
    [
        (1, 25, 0, 0, False, False),
        (1, 25, 1, 1, False, False),
        (1, 25, 26, 2, False, True),
        (2, 25, 26, 2, True, False),
        (3, 10, 25, 3, True, False),
    ],
)
def test_pagination_meta_calculates_page_boundaries(
    page: int,
    page_size: int,
    total: int,
    total_pages: int,
    previous: bool,
    next_page: bool,
) -> None:
    meta = PaginationMeta.from_total(
        page=page,
        page_size=page_size,
        total_items=total,
    )

    assert meta.total_pages == total_pages
    assert meta.has_previous is previous
    assert meta.has_next is next_page


@pytest.mark.parametrize(
    ("page", "page_size", "total"),
    [(0, 25, 1), (1, 0, 1), (1, 25, -1)],
)
def test_pagination_meta_rejects_invalid_calculation_input(
    page: int,
    page_size: int,
    total: int,
) -> None:
    with pytest.raises(ValueError):
        PaginationMeta.from_total(
            page=page,
            page_size=page_size,
            total_items=total,
        )


def test_pagination_meta_schema_rejects_inconsistent_negative_values() -> None:
    with pytest.raises(ValidationError):
        PaginationMeta(
            page=1,
            page_size=25,
            total_items=-1,
            total_pages=0,
            has_previous=False,
            has_next=False,
        )


def test_list_response_includes_items_and_current_query_summary() -> None:
    response = build_list_response(
        items=(ExampleItem(id=1), ExampleItem(id=2)),
        total_items=28,
        page=PageParams(page=2, page_size=2),
        sort=SortParams[ExampleSortField](
            sort_by=ExampleSortField.CREATED_AT,
            sort_direction=SortDirection.DESC,
        ),
        filters=ExampleFilters(keyword="carton"),
    )

    assert [item.id for item in response.items] == [1, 2]
    assert response.meta.pagination.total_pages == 14
    assert response.meta.sort.model_dump(mode="json") == {
        "field": "created_at",
        "direction": "desc",
    }
    assert response.meta.filters.model_dump() == {"keyword": "carton"}
