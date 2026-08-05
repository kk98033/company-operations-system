from datetime import date

import pytest
from pydantic import ValidationError

from app.api.contracts import DateRangeParams, KeywordParams, PageParams


def test_page_params_use_bounded_defaults_and_calculate_offset() -> None:
    first_page = PageParams()
    third_page = PageParams(page=3, page_size=40)

    assert first_page.model_dump() == {"page": 1, "page_size": 25}
    assert first_page.offset == 0
    assert third_page.offset == 80


@pytest.mark.parametrize(
    ("values", "field"),
    [
        ({"page": 0}, "page"),
        ({"page": 1_000_001}, "page"),
        ({"page_size": 0}, "page_size"),
        ({"page_size": 101}, "page_size"),
    ],
)
def test_page_params_reject_unbounded_values(
    values: dict[str, int],
    field: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        PageParams.model_validate(values)

    assert error.value.errors()[0]["loc"] == (field,)


def test_keyword_params_trim_text_and_normalize_blank_input() -> None:
    assert KeywordParams(keyword="  carton  ").keyword == "carton"
    assert KeywordParams(keyword="   ").keyword is None


def test_keyword_params_reject_overly_long_input() -> None:
    with pytest.raises(ValidationError):
        KeywordParams(keyword="x" * 101)


def test_date_range_accepts_open_and_equal_boundaries() -> None:
    open_range = DateRangeParams(date_from=date(2026, 8, 1))
    one_day = DateRangeParams(
        date_from=date(2026, 8, 5),
        date_to=date(2026, 8, 5),
    )

    assert open_range.date_to is None
    assert one_day.date_from == one_day.date_to


def test_date_range_rejects_inverted_boundaries() -> None:
    with pytest.raises(ValidationError) as error:
        DateRangeParams(
            date_from=date(2026, 8, 6),
            date_to=date(2026, 8, 5),
        )

    assert "date_from must be earlier" in str(error.value)
