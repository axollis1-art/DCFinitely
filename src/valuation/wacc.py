"""CAPM and weighted average cost of capital calculations."""

from __future__ import annotations

from src.utils.validation import FinancialModelError, require_finite, require_non_negative, require_rate


def calculate_cost_of_equity(
    risk_free_rate: float, beta: float, equity_risk_premium: float
) -> float:
    """Calculate CAPM cost of equity: risk-free rate + beta × ERP."""
    require_rate(risk_free_rate, "Risk-free rate", minimum=-1.0)
    require_finite(beta, "Beta")
    require_rate(equity_risk_premium, "Equity risk premium", minimum=-1.0)
    return risk_free_rate + beta * equity_risk_premium


def calculate_wacc(
    *,
    market_value_equity: float,
    market_value_debt: float,
    cost_of_equity: float,
    cost_of_debt: float,
    tax_rate: float,
) -> float:
    """Calculate WACC using market-value capital weights and tax-shielded debt."""
    equity = require_non_negative(market_value_equity, "Market value of equity")
    debt = require_non_negative(market_value_debt, "Market value of debt")
    if equity + debt == 0:
        raise FinancialModelError("At least one of market value of equity or debt must be positive.")
    require_rate(cost_of_equity, "Cost of equity", minimum=-1.0)
    require_rate(cost_of_debt, "Cost of debt", minimum=-1.0)
    require_rate(tax_rate, "Tax rate")
    if tax_rate > 1:
        raise FinancialModelError("Tax rate cannot exceed 100%.")

    capital = equity + debt
    equity_weight = equity / capital
    debt_weight = debt / capital
    return equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)
