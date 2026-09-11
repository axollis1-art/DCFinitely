"""Tests for the pure DCF workflow used by the Streamlit interface."""

import pytest

from src.data.provider import CompanyFinancials
from src.valuation.workflow import calculate_valuation_workflow, derive_forecast_defaults, derive_wacc_defaults


def test_defaults_are_derived_from_latest_historical_data(company: CompanyFinancials) -> None:
    defaults = derive_forecast_defaults(company)

    assert defaults.revenue_growth == pytest.approx((0.10,) * 5)
    assert defaults.operating_margin == pytest.approx((0.20,) * 5)
    assert defaults.capex_as_pct_revenue == pytest.approx((0.07,) * 5)


def test_workflow_composes_existing_financial_model(company: CompanyFinancials) -> None:
    forecast_defaults = derive_forecast_defaults(company)
    wacc_defaults = derive_wacc_defaults(company)

    result = calculate_valuation_workflow(company, forecast_defaults, wacc_defaults)

    assert len(result.forecast) == 5
    assert result.cost_of_equity == pytest.approx(0.095)
    assert result.wacc > 0
    assert result.valuation.implied_share_price > 0
