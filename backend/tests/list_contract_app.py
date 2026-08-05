"""Test-only endpoint demonstrating the reusable list contract composition."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.api.contracts import (
    DateRangeParams,
    KeywordParams,
    ListResponse,
    PageParams,
    SortDirection,
    SortParams,
    build_list_response,
    parse_date_range_params,
)


class ExampleSortField(StrEnum):
    """Endpoint-owned whitelist used only by contract tests."""

    CREATED_AT = "created_at"
    NAME = "name"


class ExampleSortParams(SortParams[ExampleSortField]):
    sort_by: ExampleSortField = ExampleSortField.CREATED_AT
    sort_direction: SortDirection = SortDirection.DESC


class ExampleItem(BaseModel):
    id: int
    name: str


class ExampleFilterSummary(BaseModel):
    keyword: str | None
    date_from: date | None
    date_to: date | None


ExampleListResponse = ListResponse[ExampleItem, ExampleFilterSummary]


def register_list_contract_route(app: FastAPI) -> None:
    """Register a test route without adding any production business endpoint."""

    @app.get("/_test/examples", response_model=ExampleListResponse)
    def list_examples(
        page: Annotated[PageParams, Depends()],
        sort: Annotated[ExampleSortParams, Depends()],
        search: Annotated[KeywordParams, Depends()],
        dates: Annotated[DateRangeParams, Depends(parse_date_range_params)],
    ) -> ExampleListResponse:
        response = build_list_response(
            items=[ExampleItem(id=1, name="Example")],
            total_items=26,
            page=page,
            sort=sort,
            filters=ExampleFilterSummary(
                keyword=search.keyword,
                date_from=dates.date_from,
                date_to=dates.date_to,
            ),
        )
        return ExampleListResponse.model_validate(response)
