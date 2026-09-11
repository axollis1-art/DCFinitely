"""Pure orchestration for an end-to-end DCF valuation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from src.data.provider import CompanyFinancials
from src.financials.forecasts import FORECAST_YEARS, ForecastYear, build_five_year_forecast
from src.utils.validation import FinancialModelError
from src.valuation.dcf import DcfValuation, calculate_dcf_valuation
from src.valuation.wacc import calculate_cost_of_equity, calculate_wacc


@dataclass(frozen=True)
class ForecastAssumptions:
    """Editable annual operating assumptions, expressed as decimal rates."""

    revenue_growth: tuple[float, ...]
    operating_margin: tuple[float, ...]
    tax_rate: tuple[float, ...]
    depreciation_as_pct_revenue: tuple[float, ...]
    capex_as_pct_revenue: tuple[float, ...]
    nwc_as_pct_revenue: tuple[float, ...]


@dataclass(frozen=True)
class WaccAssumptions:
    """Editable capital-market inputs for CAPM, WACC, and terminal value."""

    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    cost_of_debt: float
    market_value_equity: float
    market_value_debt: float
    tax_rate: float
    terminal_growth_rate: float
    cash: float
    diluted_shares_outstanding: float


@dataclass(frozen=True)
class ValuationResult:
    """All outputs needed to render an inspectable DCF workflow."""

    forecast: tuple[ForecastYear, ...]
    cost_of_equity: float
    wacc: float
    valuation: DcfValuation


def derive_forecast_defaults(company: CompanyFinancials) -> ForecastAssumptions:
    """Derive cautious, visible starting assumptions from company history.

    Missing or unusable historical values fall back to simple, documented
    estimates. These are user assumptions, not externally sourced forecasts.
    """
    periods = company.historical_financials
    revenues = [period.revenue for period in periods if period.revenue and period.revenue > 0]
    growth_rates = [
        current / previous - 1
        for previous, current in zip(revenues, revenues[1:], strict=False)
        if previous > 0
    ]
    revenue_growth = _bounded(median(growth_rates), -0.25, 0.30) if growth_rates else 0.05
    latest = periods[-1] if periods else None
    operating_margin = _ratio(latest and latest.operating_income, latest and latest.revenue, 0.15)
    tax_rate = _bounded(latest.effective_tax_rate if latest and latest.effective_tax_rate is not None else 0.25, 0.0, 0.50)
    depreciation_rate = _bounded(
        _ratio(latest and latest.depreciation_and_amortisation, latest and latest.revenue, 0.03),
        0.0,
        0.25,
    )
    capex_rate = _bounded(_ratio(latest and latest.capex, latest and latest.revenue, 0.04), 0.0, 0.30)
    nwc_rate = _bounded(_ratio(latest and latest.net_working_capital, latest and latest.revenue, 0.10), 0.0, 0.50)
    return ForecastAssumptions(
        revenue_growth=(revenue_growth,) * FORECAST_YEARS,
        operating_margin=(operating_margin,) * FORECAST_YEARS,
        tax_rate=(tax_rate,) * FORECAST_YEARS,
        depreciation_as_pct_revenue=(depreciation_rate,) * FORECAST_YEARS,
        capex_as_pct_revenue=(capex_rate,) * FORECAST_YEARS,
        nwc_as_pct_revenue=(nwc_rate,) * FORECAST_YEARS,
    )


def derive_wacc_defaults(company: CompanyFinancials) -> WaccAssumptions:
    """Provide editable WACC defaults, preferring provider values when present."""
    latest = company.historical_financials[-1] if company.historical_financials else None
    tax_rate = latest.effective_tax_rate if latest and latest.effective_tax_rate is not None else 0.25
    return WaccAssumptions(
        risk_free_rate=0.04,
        equity_risk_premium=0.05,
        beta=company.beta if company.beta is not None else 1.0,
        cost_of_debt=0.05,
        market_value_equity=company.market_capitalisation or 0.0,
        market_value_debt=company.total_debt or 0.0,
        tax_rate=_bounded(tax_rate, 0.0, 0.50),
        terminal_growth_rate=0.025,
        cash=company.cash or 0.0,
        diluted_shares_outstanding=company.diluted_shares_outstanding or 0.0,
    )


def calculate_valuation_workflow(
    company: CompanyFinancials,
    forecast_assumptions: ForecastAssumptions,
    wacc_assumptions: WaccAssumptions,
) -> ValuationResult:
    """Run the existing DCF engine using sourced data and user assumptions."""
    if not company.historical_financials:
        raise FinancialModelError("No historical financial periods are available for forecasting.")
    latest = company.historical_financials[-1]
    if latest.revenue is None:
        raise FinancialModelError("Latest revenue is unavailable; enter a ticker with annual revenue data.")
    base_nwc = latest.net_working_capital if latest.net_working_capital is not None else 0.0
    if base_nwc < 0:
        raise FinancialModelError("Negative net working capital is not supported by the initial forecast model.")

    forecast = build_five_year_forecast(
        base_revenue=latest.revenue,
        base_net_working_capital=base_nwc,
        revenue_growth=forecast_assumptions.revenue_growth,
        operating_margin=forecast_assumptions.operating_margin,
        tax_rate=forecast_assumptions.tax_rate,
        depreciation_as_pct_revenue=forecast_assumptions.depreciation_as_pct_revenue,
        capex_as_pct_revenue=forecast_assumptions.capex_as_pct_revenue,
        nwc_as_pct_revenue=forecast_assumptions.nwc_as_pct_revenue,
    )
    cost_of_equity = calculate_cost_of_equity(
        wacc_assumptions.risk_free_rate,
        wacc_assumptions.beta,
        wacc_assumptions.equity_risk_premium,
    )
    wacc = calculate_wacc(
        market_value_equity=wacc_assumptions.market_value_equity,
        market_value_debt=wacc_assumptions.market_value_debt,
        cost_of_equity=cost_of_equity,
        cost_of_debt=wacc_assumptions.cost_of_debt,
        tax_rate=wacc_assumptions.tax_rate,
    )
    valuation = calculate_dcf_valuation(
        forecast_ufcfs=[year.ufcf for year in forecast],
        wacc=wacc,
        terminal_growth_rate=wacc_assumptions.terminal_growth_rate,
        debt=wacc_assumptions.market_value_debt,
        cash=wacc_assumptions.cash,
        diluted_shares_outstanding=wacc_assumptions.diluted_shares_outstanding,
    )
    return ValuationResult(forecast=forecast, cost_of_equity=cost_of_equity, wacc=wacc, valuation=valuation)


def _ratio(numerator: float | None, denominator: float | None, fallback: float) -> float:
    if numerator is None or denominator is None or denominator <= 0:
        return fallback
    return numerator / denominator


def _bounded(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
