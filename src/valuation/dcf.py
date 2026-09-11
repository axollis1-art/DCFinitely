"""Discounted cash flow valuation bridge."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from src.utils.validation import FinancialModelError, require_finite, require_non_negative, require_rate
from src.valuation.terminal_value import calculate_gordon_growth_terminal_value


def discount_factor(discount_rate: float, period: int) -> float:
    """Return the factor used to discount a cash flow in a future period."""
    require_rate(discount_rate, "Discount rate", minimum=-1.0)
    if period < 1:
        raise FinancialModelError("Discount period must be at least one.")
    return 1 / (1 + discount_rate) ** period


def present_value(cash_flow: float, discount_rate: float, period: int) -> float:
    """Discount one future cash flow to present value."""
    require_finite(cash_flow, "Cash flow")
    return cash_flow * discount_factor(discount_rate, period)


def present_value_of_cash_flows(cash_flows: Sequence[float], discount_rate: float) -> float:
    """Return the summed present value of sequential annual cash flows."""
    if not cash_flows:
        raise FinancialModelError("At least one forecast cash flow is required.")
    return sum(present_value(cash_flow, discount_rate, period) for period, cash_flow in enumerate(cash_flows, start=1))


@dataclass(frozen=True)
class DcfValuation:
    """An inspectable bridge from operating cash flow to implied share price."""

    present_value_of_explicit_cash_flows: float
    terminal_value: float
    present_value_of_terminal_value: float
    enterprise_value: float
    debt: float
    cash: float
    equity_value: float
    diluted_shares_outstanding: float
    implied_share_price: float


def calculate_dcf_valuation(
    *,
    forecast_ufcfs: Sequence[float],
    wacc: float,
    terminal_growth_rate: float,
    debt: float,
    cash: float,
    diluted_shares_outstanding: float,
) -> DcfValuation:
    """Calculate the complete DCF bridge from forecast UFCF to share price."""
    if not forecast_ufcfs:
        raise FinancialModelError("At least one forecast UFCF is required.")
    require_non_negative(debt, "Debt")
    require_non_negative(cash, "Cash")
    shares = require_non_negative(diluted_shares_outstanding, "Diluted shares outstanding")
    if shares == 0:
        raise FinancialModelError("Diluted shares outstanding must be greater than zero.")

    pv_explicit = present_value_of_cash_flows(forecast_ufcfs, wacc)
    terminal_value = calculate_gordon_growth_terminal_value(
        forecast_ufcfs[-1], wacc, terminal_growth_rate
    )
    pv_terminal = present_value(terminal_value, wacc, len(forecast_ufcfs))
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - debt + cash
    return DcfValuation(
        present_value_of_explicit_cash_flows=pv_explicit,
        terminal_value=terminal_value,
        present_value_of_terminal_value=pv_terminal,
        enterprise_value=enterprise_value,
        debt=debt,
        cash=cash,
        equity_value=equity_value,
        diluted_shares_outstanding=shares,
        implied_share_price=equity_value / shares,
    )
