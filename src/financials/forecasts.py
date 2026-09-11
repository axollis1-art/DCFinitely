"""Five-year operating forecast construction for DCF valuations."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from src.financials.metrics import calculate_ufcf
from src.utils.validation import FinancialModelError, require_non_negative, require_rate


FORECAST_YEARS = 5


@dataclass(frozen=True)
class ForecastYear:
    """Inspectable operating and cash-flow outputs for one forecast period."""

    period: int
    revenue: float
    ebit: float
    tax_rate: float
    depreciation_and_amortisation: float
    capex: float
    net_working_capital: float
    change_in_nwc: float
    ufcf: float


def _validate_assumption_series(name: str, values: Sequence[float]) -> tuple[float, ...]:
    """Validate a five-year series of decimal assumptions."""
    series = tuple(values)
    if len(series) != FORECAST_YEARS:
        raise FinancialModelError(f"{name} must contain exactly {FORECAST_YEARS} years.")
    for value in series:
        require_rate(value, name, minimum=-1.0)
    return series


def build_five_year_forecast(
    *,
    base_revenue: float,
    base_net_working_capital: float,
    revenue_growth: Sequence[float],
    operating_margin: Sequence[float],
    tax_rate: Sequence[float],
    depreciation_as_pct_revenue: Sequence[float],
    capex_as_pct_revenue: Sequence[float],
    nwc_as_pct_revenue: Sequence[float],
) -> tuple[ForecastYear, ...]:
    """Build a five-year operating forecast and its associated UFCF.

    Each assumption is a five-item sequence of decimal rates. Net working
    capital is modelled as a percentage of revenue; the first forecast year's
    change is measured against ``base_net_working_capital``.
    """
    require_non_negative(base_revenue, "Base revenue")
    require_non_negative(base_net_working_capital, "Base net working capital")
    growth = _validate_assumption_series("Revenue growth", revenue_growth)
    margin = _validate_assumption_series("Operating margin", operating_margin)
    taxes = _validate_assumption_series("Tax rate", tax_rate)
    da_rate = _validate_assumption_series("D&A as a percentage of revenue", depreciation_as_pct_revenue)
    capex_rate = _validate_assumption_series("Capex as a percentage of revenue", capex_as_pct_revenue)
    nwc_rate = _validate_assumption_series("NWC as a percentage of revenue", nwc_as_pct_revenue)

    if any(rate > 1 for rate in taxes):
        raise FinancialModelError("Tax rate cannot exceed 100%.")
    if any(rate < 0 for rate in da_rate + capex_rate + nwc_rate):
        raise FinancialModelError("D&A, capex, and NWC percentages cannot be negative.")

    years: list[ForecastYear] = []
    revenue = base_revenue
    previous_nwc = base_net_working_capital
    for period in range(FORECAST_YEARS):
        revenue *= 1 + growth[period]
        ebit = revenue * margin[period]
        depreciation_and_amortisation = revenue * da_rate[period]
        capex = revenue * capex_rate[period]
        net_working_capital = revenue * nwc_rate[period]
        change_in_nwc = net_working_capital - previous_nwc
        ufcf = calculate_ufcf(
            ebit,
            taxes[period],
            depreciation_and_amortisation,
            capex,
            change_in_nwc,
        )
        years.append(
            ForecastYear(
                period=period + 1,
                revenue=revenue,
                ebit=ebit,
                tax_rate=taxes[period],
                depreciation_and_amortisation=depreciation_and_amortisation,
                capex=capex,
                net_working_capital=net_working_capital,
                change_in_nwc=change_in_nwc,
                ufcf=ufcf,
            )
        )
        previous_nwc = net_working_capital
    return tuple(years)
