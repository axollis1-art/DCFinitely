"""Decision-useful Plotly figures for the DCF workflow."""

from __future__ import annotations

from collections.abc import Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data.provider import CompanyFinancials
from src.financials.forecasts import ForecastYear
from src.valuation.dcf import DcfValuation


def revenue_chart(company: CompanyFinancials, forecast: Sequence[ForecastYear]) -> go.Figure:
    """Show the revenue transition from sourced history to forecast."""
    historical_periods = [period.period_end.year for period in company.historical_financials]
    historical_revenue = [period.revenue for period in company.historical_financials]
    forecast_periods = [historical_periods[-1] + year.period for year in forecast] if historical_periods else []
    figure = go.Figure()
    figure.add_scatter(x=historical_periods, y=historical_revenue, mode="lines+markers", name="Historical (sourced)")
    figure.add_scatter(x=forecast_periods, y=[year.revenue for year in forecast], mode="lines+markers", name="Forecast")
    return _style(figure, "Revenue", "Reporting year", "Revenue")


def ebit_margin_chart(company: CompanyFinancials, forecast: Sequence[ForecastYear]) -> go.Figure:
    """Compare historical and forecast operating income and margin."""
    historical_periods = [period.period_end.year for period in company.historical_financials]
    historical_ebit = [period.operating_income for period in company.historical_financials]
    historical_margin = [
        period.operating_income / period.revenue if period.operating_income is not None and period.revenue else None
        for period in company.historical_financials
    ]
    forecast_periods = [historical_periods[-1] + year.period for year in forecast] if historical_periods else []
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_bar(x=historical_periods, y=historical_ebit, name="Historical EBIT (sourced)")
    figure.add_bar(x=forecast_periods, y=[year.ebit for year in forecast], name="Forecast EBIT")
    figure.add_scatter(x=historical_periods, y=historical_margin, mode="lines+markers", name="Historical margin", secondary_y=True)
    figure.add_scatter(x=forecast_periods, y=[year.ebit / year.revenue for year in forecast], mode="lines+markers", name="Forecast margin", secondary_y=True)
    figure.update_yaxes(title_text="EBIT", secondary_y=False)
    figure.update_yaxes(title_text="Operating margin", tickformat=".1%", secondary_y=True)
    return _style(figure, "Operating performance", "Reporting year", None)


def ufcf_chart(forecast: Sequence[ForecastYear], latest_year: int) -> go.Figure:
    """Show forecast unlevered free cash flow by year."""
    figure = go.Figure(
        go.Bar(
            x=[latest_year + year.period for year in forecast],
            y=[year.ufcf for year in forecast],
            name="Forecast UFCF",
        )
    )
    return _style(figure, "Projected unlevered free cash flow", "Forecast year", "UFCF")


def valuation_bridge_chart(valuation: DcfValuation) -> go.Figure:
    """Show the bridge from discounted cash flow to equity value."""
    figure = go.Figure(
        go.Waterfall(
            name="DCF bridge",
            orientation="v",
            measure=["relative", "relative", "relative", "relative", "total"],
            x=["PV explicit UFCF", "PV terminal value", "Debt", "Cash", "Equity value"],
            y=[
                valuation.present_value_of_explicit_cash_flows,
                valuation.present_value_of_terminal_value,
                -valuation.debt,
                valuation.cash,
                valuation.equity_value,
            ],
            connector={"line": {"color": "#64748b"}},
        )
    )
    return _style(figure, "DCF valuation bridge", "", "Value")


def _style(figure: go.Figure, title: str, x_title: str, y_title: str | None) -> go.Figure:
    figure.update_layout(template="plotly_white", title=title, legend_title_text="")
    figure.update_xaxes(title_text=x_title)
    if y_title:
        figure.update_yaxes(title_text=y_title)
    return figure
