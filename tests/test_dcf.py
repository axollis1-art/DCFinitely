"""Tests for DCF discounting, terminal value, and valuation bridge."""

import pytest

from src.utils.validation import FinancialModelError
from src.valuation.dcf import calculate_dcf_valuation, discount_factor, present_value, present_value_of_cash_flows
from src.valuation.terminal_value import calculate_gordon_growth_terminal_value


def test_discount_factor_and_present_value_of_cash_flows() -> None:
    assert discount_factor(0.10, 2) == pytest.approx(1 / 1.21)
    assert present_value(121.0, 0.10, 2) == pytest.approx(100.0)
    assert present_value_of_cash_flows([100.0, 100.0], 0.10) == pytest.approx(173.553719)


def test_discount_factor_rejects_a_non_future_period() -> None:
    with pytest.raises(FinancialModelError, match="at least one"):
        discount_factor(0.10, 0)


def test_gordon_growth_terminal_value() -> None:
    assert calculate_gordon_growth_terminal_value(100.0, 0.10, 0.03) == pytest.approx(1471.428571)


def test_gordon_growth_rejects_invalid_wacc_growth_pair() -> None:
    with pytest.raises(FinancialModelError, match="greater than"):
        calculate_gordon_growth_terminal_value(100.0, 0.03, 0.03)


def test_calculate_dcf_valuation_exposes_equity_bridge() -> None:
    valuation = calculate_dcf_valuation(
        forecast_ufcfs=[100.0, 110.0, 120.0, 130.0, 140.0],
        wacc=0.10,
        terminal_growth_rate=0.03,
        debt=200.0,
        cash=50.0,
        diluted_shares_outstanding=100.0,
    )

    assert valuation.enterprise_value == pytest.approx(
        valuation.present_value_of_explicit_cash_flows + valuation.present_value_of_terminal_value
    )
    assert valuation.equity_value == pytest.approx(valuation.enterprise_value - 200.0 + 50.0)
    assert valuation.implied_share_price == pytest.approx(valuation.equity_value / 100.0)


def test_calculate_dcf_valuation_rejects_zero_shares() -> None:
    with pytest.raises(FinancialModelError, match="greater than zero"):
        calculate_dcf_valuation(
            forecast_ufcfs=[100.0],
            wacc=0.10,
            terminal_growth_rate=0.03,
            debt=0.0,
            cash=0.0,
            diluted_shares_outstanding=0.0,
        )


@pytest.mark.parametrize("debt,cash", [(-1.0, 0.0), (0.0, -1.0)])
def test_calculate_dcf_valuation_rejects_negative_balance_sheet_inputs(debt: float, cash: float) -> None:
    with pytest.raises(FinancialModelError, match="cannot be negative"):
        calculate_dcf_valuation(
            forecast_ufcfs=[100.0],
            wacc=0.10,
            terminal_growth_rate=0.03,
            debt=debt,
            cash=cash,
            diluted_shares_outstanding=10.0,
        )
