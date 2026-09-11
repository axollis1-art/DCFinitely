"""Streamlit entry point for the DCFinitely valuation platform."""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.data.provider import DataProviderError, FinancialDataError
from src.data.yfinance_provider import YFinanceProvider
from src.financials.forecasts import FORECAST_YEARS
from src.utils.validation import FinancialModelError
from src.valuation.workflow import (
    ForecastAssumptions,
    WaccAssumptions,
    calculate_valuation_workflow,
    derive_forecast_defaults,
    derive_wacc_defaults,
)
from src.valuation.sensitivity import SensitivityTable, generate_sensitivity_table
from src.visualisation.charts import ebit_margin_chart, revenue_chart, ufcf_chart, valuation_bridge_chart


st.set_page_config(page_title="DCFinitely", page_icon="DCF", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def load_company_financials(ticker: str):
    """Cache public-data requests while preserving provider-specific errors."""
    return YFinanceProvider().get_company_financials(ticker)


def percentage_series_inputs(label: str, defaults: tuple[float, ...], key: str) -> tuple[float, ...]:
    """Render five editable percentage inputs and return decimal rates."""
    with st.sidebar.expander(label, expanded=False):
        values = [
            st.number_input(
                f"Year {year}",
                value=float(default * 100),
                step=0.5,
                format="%.1f",
                key=f"{key}_{year}",
            )
            / 100
            for year, default in enumerate(defaults, start=1)
        ]
    return tuple(values)


def currency(value: float | None, currency_code: str | None) -> str:
    """Format a reported currency amount for compact dashboard metrics."""
    if value is None:
        return "Unavailable"
    prefix = f"{currency_code} " if currency_code else ""
    return f"{prefix}{value:,.0f}"


st.title("DCFinitely")
st.caption("Transparent discounted cash flow valuation for public companies.")
st.caption("Educational use only — not investment advice.")

with st.form("ticker_lookup"):
    ticker = st.text_input("Company ticker", placeholder="e.g. AAPL", help="Uses public Yahoo Finance data via yfinance.")
    lookup_requested = st.form_submit_button("Load company")

if lookup_requested:
    try:
        with st.spinner("Retrieving annual financial statements..."):
            st.session_state["company_financials"] = load_company_financials(ticker)
    except FinancialDataError as error:
        st.error(str(error))
        st.session_state.pop("company_financials", None)

company = st.session_state.get("company_financials")
if company is None:
    st.info("Enter a public-company ticker to begin an inspectable valuation.")
    st.stop()

st.header("1. Company overview")
overview = st.columns(4)
overview[0].metric("Company", company.company_name or company.ticker)
overview[1].metric("Market capitalisation", currency(company.market_capitalisation, company.currency))
overview[2].metric("Cash", currency(company.cash, company.currency))
overview[3].metric("Total debt", currency(company.total_debt, company.currency))
st.caption(f"Source: {company.source}. Retrieved {company.retrieved_at:%Y-%m-%d %H:%M UTC}.")
if company.missing_data_message:
    st.warning(company.missing_data_message)

st.header("2. Historical financials")
historical = company.historical_dataframe().rename(
    columns={
        "period_end": "Period end (sourced)",
        "revenue": "Revenue (sourced)",
        "operating_income": "EBIT / operating income (sourced)",
        "tax_expense": "Tax expense (sourced)",
        "pretax_income": "Pre-tax income (sourced)",
        "effective_tax_rate": "Effective tax rate (derived)",
        "depreciation_and_amortisation": "D&A (sourced)",
        "capex": "Capex (sourced; positive outflow)",
        "change_in_nwc": "Change in NWC (normalised)",
        "current_assets": "Current assets (sourced)",
        "current_liabilities": "Current liabilities (sourced)",
        "net_working_capital": "Net working capital (derived)",
    }
)
st.dataframe(historical, use_container_width=True, hide_index=True)

forecast_defaults = derive_forecast_defaults(company)
wacc_defaults = derive_wacc_defaults(company)
st.sidebar.header("Valuation assumptions")
st.sidebar.caption("All sidebar inputs are editable user assumptions. Rates are percentages.")

st.sidebar.subheader("Forecast assumptions")
forecast_assumptions = ForecastAssumptions(
    revenue_growth=percentage_series_inputs("Revenue growth", forecast_defaults.revenue_growth, f"{company.ticker}_growth"),
    operating_margin=percentage_series_inputs("Operating margin", forecast_defaults.operating_margin, f"{company.ticker}_margin"),
    tax_rate=percentage_series_inputs("Tax rate", forecast_defaults.tax_rate, f"{company.ticker}_tax"),
    depreciation_as_pct_revenue=percentage_series_inputs("D&A as % of revenue", forecast_defaults.depreciation_as_pct_revenue, f"{company.ticker}_da"),
    capex_as_pct_revenue=percentage_series_inputs("Capex as % of revenue", forecast_defaults.capex_as_pct_revenue, f"{company.ticker}_capex"),
    nwc_as_pct_revenue=percentage_series_inputs("NWC as % of revenue", forecast_defaults.nwc_as_pct_revenue, f"{company.ticker}_nwc"),
)

st.sidebar.subheader("WACC assumptions")
st.sidebar.caption("Risk-free rate, ERP, and debt cost are editable modelling assumptions, not live market data.")
with st.sidebar.expander("WACC and capital structure", expanded=True):
    risk_free_rate = st.number_input("Risk-free rate", value=wacc_defaults.risk_free_rate * 100, step=0.25, format="%.2f", key=f"{company.ticker}_rf") / 100
    equity_risk_premium = st.number_input("Equity risk premium", value=wacc_defaults.equity_risk_premium * 100, step=0.25, format="%.2f", key=f"{company.ticker}_erp") / 100
    beta = st.number_input("Beta", value=wacc_defaults.beta, step=0.05, key=f"{company.ticker}_beta")
    cost_of_debt = st.number_input("Pre-tax cost of debt", value=wacc_defaults.cost_of_debt * 100, step=0.25, format="%.2f", key=f"{company.ticker}_cod") / 100
    wacc_tax_rate = st.number_input("WACC tax rate", value=wacc_defaults.tax_rate * 100, step=0.5, format="%.1f", key=f"{company.ticker}_wacc_tax") / 100
    terminal_growth_rate = st.number_input("Terminal growth rate", value=wacc_defaults.terminal_growth_rate * 100, step=0.25, format="%.2f", key=f"{company.ticker}_terminal_growth") / 100
    market_value_equity = st.number_input("Market value of equity", value=wacc_defaults.market_value_equity, step=1_000_000.0, key=f"{company.ticker}_equity")
    market_value_debt = st.number_input("Market value of debt", value=wacc_defaults.market_value_debt, step=1_000_000.0, key=f"{company.ticker}_debt")
    cash = st.number_input("Cash", value=wacc_defaults.cash, step=1_000_000.0, key=f"{company.ticker}_cash")
    shares = st.number_input("Diluted shares outstanding", value=wacc_defaults.diluted_shares_outstanding, step=1_000_000.0, key=f"{company.ticker}_shares")

wacc_assumptions = WaccAssumptions(
    risk_free_rate=risk_free_rate,
    equity_risk_premium=equity_risk_premium,
    beta=beta,
    cost_of_debt=cost_of_debt,
    market_value_equity=market_value_equity,
    market_value_debt=market_value_debt,
    tax_rate=wacc_tax_rate,
    terminal_growth_rate=terminal_growth_rate,
    cash=cash,
    diluted_shares_outstanding=shares,
)

st.header("3. Forecast assumptions")
assumptions_table = pd.DataFrame(
    {
        "Year": list(range(1, FORECAST_YEARS + 1)),
        "Revenue growth (user assumption)": forecast_assumptions.revenue_growth,
        "Operating margin (user assumption)": forecast_assumptions.operating_margin,
        "Tax rate (user assumption)": forecast_assumptions.tax_rate,
        "D&A / revenue (user assumption)": forecast_assumptions.depreciation_as_pct_revenue,
        "Capex / revenue (user assumption)": forecast_assumptions.capex_as_pct_revenue,
        "NWC / revenue (user assumption)": forecast_assumptions.nwc_as_pct_revenue,
    }
)
st.dataframe(assumptions_table.style.format({column: "{:.1%}" for column in assumptions_table.columns[1:]}), use_container_width=True, hide_index=True)

try:
    result = calculate_valuation_workflow(company, forecast_assumptions, wacc_assumptions)
except FinancialModelError as error:
    st.error(f"Valuation cannot be calculated: {error}")
    st.stop()

st.header("4. Forecast financials")
forecast_table = pd.DataFrame([asdict(year) for year in result.forecast]).rename(columns={"period": "Forecast year"})
st.dataframe(forecast_table, use_container_width=True, hide_index=True)
st.plotly_chart(revenue_chart(company, result.forecast), use_container_width=True)
st.plotly_chart(ebit_margin_chart(company, result.forecast), use_container_width=True)
st.plotly_chart(ufcf_chart(result.forecast, company.historical_financials[-1].period_end.year), use_container_width=True)

st.header("5. WACC")
wacc_table = pd.DataFrame(
    {
        "Component": ["Risk-free rate", "Beta", "Equity risk premium", "Cost of equity (CAPM)", "Cost of debt", "Tax rate", "WACC"],
        "Value": [
            f"{risk_free_rate:.2%}",
            f"{beta:.2f}",
            f"{equity_risk_premium:.2%}",
            f"{result.cost_of_equity:.2%}",
            f"{cost_of_debt:.2%}",
            f"{wacc_tax_rate:.2%}",
            f"{result.wacc:.2%}",
        ],
    }
)
st.dataframe(wacc_table, use_container_width=True, hide_index=True)

st.header("6. DCF valuation")
valuation = result.valuation
valuation_metrics = st.columns(4)
valuation_metrics[0].metric("Enterprise value", currency(valuation.enterprise_value, company.currency))
valuation_metrics[1].metric("Equity value", currency(valuation.equity_value, company.currency))
valuation_metrics[2].metric("Implied share price", currency(valuation.implied_share_price, company.currency))
valuation_metrics[3].metric("WACC", f"{result.wacc:.2%}")
st.plotly_chart(valuation_bridge_chart(valuation), use_container_width=True)

st.header("7. Sensitivity analysis")
st.caption("Each cell is an implied share price. The highlighted cell is the current base case.")
with st.sidebar.expander("Sensitivity table settings", expanded=False):
    sensitivity_wacc_range = st.number_input(
        "WACC range around base case", value=1.0, step=0.25, format="%.2f", key=f"{company.ticker}_sensitivity_wacc_range"
    ) / 100
    sensitivity_wacc_step = st.number_input(
        "WACC step", value=0.5, step=0.25, format="%.2f", key=f"{company.ticker}_sensitivity_wacc_step"
    ) / 100
    sensitivity_growth_range = st.number_input(
        "Terminal-growth range around base case", value=0.5, step=0.25, format="%.2f", key=f"{company.ticker}_sensitivity_growth_range"
    ) / 100
    sensitivity_growth_step = st.number_input(
        "Terminal-growth step", value=0.25, step=0.25, format="%.2f", key=f"{company.ticker}_sensitivity_growth_step"
    ) / 100

try:
    sensitivity = generate_sensitivity_table(
        forecast_ufcfs=[year.ufcf for year in result.forecast],
        base_wacc=result.wacc,
        base_terminal_growth_rate=terminal_growth_rate,
        debt=market_value_debt,
        cash=cash,
        diluted_shares_outstanding=shares,
        wacc_half_range=sensitivity_wacc_range,
        wacc_step=sensitivity_wacc_step,
        terminal_growth_half_range=sensitivity_growth_range,
        terminal_growth_step=sensitivity_growth_step,
    )
except FinancialModelError as error:
    st.warning(f"Sensitivity table unavailable: {error}")
else:
    sensitivity_frame = sensitivity.to_dataframe()
    sensitivity_frame.index = [f"{rate:.2%}" for rate in sensitivity.wacc_rates]
    sensitivity_frame.columns = [f"{rate:.2%}" for rate in sensitivity.terminal_growth_rates]

    def style_sensitivity(data: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        styles[data.isna()] = "background-color: #fee2e2; color: #991b1b"
        styles.iloc[sensitivity.base_wacc_index, sensitivity.base_terminal_growth_index] = (
            "background-color: #dcfce7; color: #166534; font-weight: bold"
        )
        return styles

    st.dataframe(
        sensitivity_frame.style.format("{:.2f}", na_rep="N/A").apply(style_sensitivity, axis=None),
        use_container_width=True,
    )
    st.caption("N/A cells are invalid because WACC is less than or equal to terminal growth.")
