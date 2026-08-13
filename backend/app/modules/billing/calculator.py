"""Decimal-only statement tax and rounding calculator."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class StatementAmounts:
    subtotal_before_rounding: Decimal
    rounding_adjustment: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    grand_total: Decimal


def _quantizer(decimal_places: int) -> Decimal:
    return Decimal(1).scaleb(-decimal_places)


def calculate_statement_amounts(
    line_amounts: list[Decimal],
    *,
    tax_enabled: bool,
    tax_rate_percent: Decimal | None,
    rounding_scope: str | None,
    rounding_decimal_places: int | None,
) -> StatementAmounts:
    raw = sum(line_amounts, Decimal("0"))
    if not tax_enabled:
        return StatementAmounts(raw, Decimal("0"), raw, Decimal("0"), raw)
    if tax_rate_percent is None or rounding_scope not in {"per_line", "grand_total"}:
        raise ValueError("enabled tax requires a complete rounding policy")
    if rounding_decimal_places is None or not 0 <= rounding_decimal_places <= 4:
        raise ValueError("invalid rounding decimal places")
    quantum = _quantizer(rounding_decimal_places)
    if rounding_scope == "per_line":
        subtotal = sum(
            (value.quantize(quantum, rounding=ROUND_HALF_UP) for value in line_amounts),
            Decimal("0"),
        )
        tax = (subtotal * tax_rate_percent / Decimal("100")).quantize(
            quantum, rounding=ROUND_HALF_UP
        )
        return StatementAmounts(raw, subtotal - raw, subtotal, tax, subtotal + tax)
    tax_raw = raw * tax_rate_percent / Decimal("100")
    rounded_total = (raw + tax_raw).quantize(quantum, rounding=ROUND_HALF_UP)
    return StatementAmounts(raw, rounded_total - raw - tax_raw, raw, tax_raw, rounded_total)
