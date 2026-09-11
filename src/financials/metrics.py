"""Financial statement metrics used by the valuation model."""

from __future__ import annotations

from src.utils.validation import require_finite, require_non_negative, require_rate


def calculate_ufcf(
    ebit: float,
    tax_rate: float,
    depreciation_and_amortisation: float,
    capex: float,
    change_in_nwc: float,
) -> float:
    """Calculate unlevered free cash flow (UFCF).

    UFCF represents cash available to all capital providers before financing
    decisions. Capex and increases in net working capital are cash outflows.

    Args:
        ebit: Earnings before interest and tax.
        tax_rate: Effective tax rate as a decimal between zero and one.
        depreciation_and_amortisation: Non-cash expense added back to EBIT.
        capex: Capital expenditure expressed as a positive cash outflow.
        change_in_nwc: Increase in net working capital; a negative value is a
            working-capital release.
    """
    require_finite(ebit, "EBIT")
    require_rate(tax_rate, "Tax rate")
    if tax_rate > 1:
        raise ValueError("Tax rate cannot exceed 100%.")
    require_non_negative(depreciation_and_amortisation, "Depreciation and amortisation")
    require_non_negative(capex, "Capex")
    require_finite(change_in_nwc, "Change in net working capital")

    nopat = ebit * (1 - tax_rate)
    return nopat + depreciation_and_amortisation - capex - change_in_nwc
