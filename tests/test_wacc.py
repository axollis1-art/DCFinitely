"""Tests for CAPM and WACC."""

import pytest

from src.utils.validation import FinancialModelError
from src.valuation.wacc import calculate_cost_of_equity, calculate_wacc


def test_calculate_cost_of_equity_uses_capm() -> None:
    assert calculate_cost_of_equity(0.04, 1.2, 0.05) == pytest.approx(0.10)


def test_calculate_wacc_uses_market_value_weights_and_tax_shield() -> None:
    result = calculate_wacc(
        market_value_equity=800.0,
        market_value_debt=200.0,
        cost_of_equity=0.10,
        cost_of_debt=0.06,
        tax_rate=0.25,
    )
    assert result == pytest.approx(0.089)


def test_calculate_wacc_rejects_empty_capital_structure() -> None:
    with pytest.raises(FinancialModelError, match="must be positive"):
        calculate_wacc(
            market_value_equity=0.0,
            market_value_debt=0.0,
            cost_of_equity=0.10,
            cost_of_debt=0.06,
            tax_rate=0.25,
        )
