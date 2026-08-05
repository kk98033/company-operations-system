"""Composable, bounded primitives for list endpoint query parameters."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

DEFAULT_PAGE_SIZE = 25
MAX_PAGE = 1_000_000
MAX_PAGE_SIZE = 100
MAX_KEYWORD_LENGTH = 100


class SortDirection(StrEnum):
    """Database-independent sort direction accepted by list endpoints."""

    ASC = "asc"
    DESC = "desc"


class PageParams(BaseModel):
    """Bounded page controls reusable by every list endpoint."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(default=1, ge=1, le=MAX_PAGE)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        """Return a safe zero-based offset for a future repository query."""

        return (self.page - 1) * self.page_size


SortField = TypeVar("SortField", bound=StrEnum)


class SortParams(BaseModel, Generic[SortField]):
    """Sort input whose field enum must be owned by the endpoint's domain."""

    model_config = ConfigDict(frozen=True)

    sort_by: SortField
    sort_direction: SortDirection = SortDirection.ASC


class KeywordParams(BaseModel):
    """Validated free text that a domain may compose into its own filters."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    keyword: str | None = Field(default=None, max_length=MAX_KEYWORD_LENGTH)

    @field_validator("keyword", mode="before")
    @classmethod
    def empty_keyword_is_none(cls, value: object) -> object:
        """Normalize optional whitespace-only searches to no filter."""

        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class DateRangeParams(BaseModel):
    """Validated inclusive generic interval for domain composition."""

    model_config = ConfigDict(frozen=True)

    date_from: date | None = None
    date_to: date | None = None

    @field_validator("date_to")
    @classmethod
    def validate_date_range(
        cls,
        date_to: date | None,
        info: ValidationInfo,
    ) -> date | None:
        """Reject inverted ranges before persistence code is called."""

        date_from = info.data.get("date_from")
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be earlier than or equal to date_to")
        return date_to


def parse_date_range_params(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> DateRangeParams:
    """Build a range dependency while preserving the API validation envelope."""

    try:
        return DateRangeParams(date_from=date_from, date_to=date_to)
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            safe_error = dict(error)
            safe_error["loc"] = ("query", *error.get("loc", ()))
            errors.append(safe_error)
        raise RequestValidationError(errors) from None
