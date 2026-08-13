"""Decimal calculator acceptance for statement tax policy."""

from decimal import Decimal

from app.modules.billing.calculator import calculate_statement_amounts


def test_tax_disabled_preserves_exact_source_amounts() -> None:
    result = calculate_statement_amounts(
        [Decimal("100.25"), Decimal("10.125")],
        tax_enabled=False,
        tax_rate_percent=None,
        rounding_scope=None,
        rounding_decimal_places=None,
    )
    assert result.subtotal_before_rounding == Decimal("110.375")
    assert result.rounding_adjustment == 0
    assert result.tax_amount == 0
    assert result.grand_total == Decimal("110.375")


def test_per_line_and_grand_total_rounding_are_explicit() -> None:
    per_line = calculate_statement_amounts(
        [Decimal("10.45"), Decimal("10.45")],
        tax_enabled=True,
        tax_rate_percent=Decimal("5"),
        rounding_scope="per_line",
        rounding_decimal_places=0,
    )
    grand = calculate_statement_amounts(
        [Decimal("10.45"), Decimal("10.45")],
        tax_enabled=True,
        tax_rate_percent=Decimal("5"),
        rounding_scope="grand_total",
        rounding_decimal_places=0,
    )
    assert per_line.subtotal == Decimal("20")
    assert per_line.tax_amount == Decimal("1")
    assert per_line.grand_total == Decimal("21")
    assert grand.subtotal == Decimal("20.90")
    assert grand.grand_total == Decimal("22")
