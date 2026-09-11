"""Tests for five-year operating forecasts."""

import pytest

from src.financials.forecasts import FORECAST_YEARS, build_five_year_forecast
from src.utils.validation import FinancialModelError


def test_build_five_year_forecast_calculates_inspectable_values() -> None:
    forecast = build_five_year_forecast(
        base_revenue=100.0,
        base_net_working_capital=10.0,
        revenue_growth=[0.10] * FORECAST_YEARS,
        operating_margin=[0.20] * FORECAST_YEARS,
        tax_rate=[0.25] * FORECAST_YEARS,
        depreciation_as_pct_revenue=[0.03] * FORECAST_YEARS,
        capex_as_pct_revenue=[0.04] * FORECAST_YEARS,
        nwc_as_pct_revenue=[0.10] * FORECAST_YEARS,
    )

    assert len(forecast) == FORECAST_YEARS
    assert forecast[0].revenue == pytest.approx(110.0)
    assert forecast[0].change_in_nwc == pytest.approx(1.0)
    assert forecast[0].ufcf == pytest.approx(14.4)
    assert forecast[-1].period == 5


def test_build_five_year_forecast_rejects_incorrect_assumption_length() -> None:
    with pytest.raises(FinancialModelError, match="exactly 5 years"):
        build_five_year_forecast(
            base_revenue=100.0,
            base_net_working_capital=10.0,
            revenue_growth=[0.1] * 4,
            operating_margin=[0.2] * 5,
            tax_rate=[0.25] * 5,
            depreciation_as_pct_revenue=[0.03] * 5,
            capex_as_pct_revenue=[0.04] * 5,
            nwc_as_pct_revenue=[0.10] * 5,
        )
