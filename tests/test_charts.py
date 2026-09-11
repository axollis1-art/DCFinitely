"""Tests that visualisations use the valuation outputs without calculations in Streamlit."""

from src.visualisation.charts import ebit_margin_chart, revenue_chart, ufcf_chart, valuation_bridge_chart
from src.valuation.workflow import calculate_valuation_workflow, derive_forecast_defaults, derive_wacc_defaults


def test_charts_render_expected_traces(company) -> None:
    result = calculate_valuation_workflow(company, derive_forecast_defaults(company), derive_wacc_defaults(company))

    assert len(revenue_chart(company, result.forecast).data) == 2
    assert len(ebit_margin_chart(company, result.forecast).data) == 4
    assert len(ufcf_chart(result.forecast, 2024).data) == 1
    assert len(valuation_bridge_chart(result.valuation).data) == 1
