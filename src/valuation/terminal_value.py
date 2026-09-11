"""Terminal-value methodologies for DCF valuation."""

from __future__ import annotations

from src.utils.validation import FinancialModelError, require_finite, require_rate


def calculate_gordon_growth_terminal_value(
    final_year_ufcf: float, wacc: float, terminal_growth_rate: float
) -> float:
    """Calculate terminal value from next year's UFCF using Gordon Growth.

    The perpetuity formula only has a finite result when WACC exceeds the
    terminal growth rate. An exit-multiple method can later live beside this
    function without affecting the DCF valuation bridge.
    """
    require_finite(final_year_ufcf, "Final-year UFCF")
    require_rate(wacc, "WACC", minimum=-1.0)
    require_rate(terminal_growth_rate, "Terminal growth rate", minimum=-1.0)
    if wacc <= terminal_growth_rate:
        raise FinancialModelError("WACC must be greater than the terminal growth rate.")
    return final_year_ufcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
