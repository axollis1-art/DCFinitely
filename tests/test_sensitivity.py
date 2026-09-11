"""Tests for framework-independent DCF sensitivity analysis."""

import pytest

from src.utils.validation import FinancialModelError
from src.valuation.dcf import calculate_dcf_valuation
from src.valuation.sensitivity import build_rate_grid, generate_sensitivity_table


def test_build_rate_grid_is_centered_on_base_case() -> None:
    assert build_rate_grid(0.10, 0.01, 0.005, "WACC") == pytest.approx((0.09, 0.095, 0.10, 0.105, 0.11))


def test_sensitivity_base_case_matches_standalone_dcf() -> None:
    forecast = [100.0, 110.0, 120.0, 130.0, 140.0]
    table = generate_sensitivity_table(
        forecast_ufcfs=forecast,
        base_wacc=0.10,
        base_terminal_growth_rate=0.03,
        debt=200.0,
        cash=50.0,
        diluted_shares_outstanding=100.0,
    )
    standalone = calculate_dcf_valuation(
        forecast_ufcfs=forecast,
        wacc=0.10,
        terminal_growth_rate=0.03,
        debt=200.0,
        cash=50.0,
        diluted_shares_outstanding=100.0,
    )

    assert table.base_wacc_index == 2
    assert table.base_terminal_growth_index == 2
    assert table.base_case_price == pytest.approx(standalone.implied_share_price)
    assert table.to_dataframe().iloc[2, 2] == pytest.approx(standalone.implied_share_price)


def test_sensitivity_marks_invalid_wacc_growth_cells_unavailable() -> None:
    table = generate_sensitivity_table(
        forecast_ufcfs=[100.0],
        base_wacc=0.03,
        base_terminal_growth_rate=0.02,
        debt=0.0,
        cash=0.0,
        diluted_shares_outstanding=10.0,
        wacc_half_range=0.01,
        wacc_step=0.01,
        terminal_growth_half_range=0.02,
        terminal_growth_step=0.02,
    )

    assert table.implied_share_prices[0][-1] is None
    assert table.implied_share_prices[-1][0] is not None
    assert table.to_dataframe().iloc[0, -1] != table.to_dataframe().iloc[0, -1]


def test_sensitivity_rejects_invalid_base_case_and_static_inputs() -> None:
    with pytest.raises(FinancialModelError, match="Base-case WACC"):
        generate_sensitivity_table(
            forecast_ufcfs=[100.0],
            base_wacc=0.03,
            base_terminal_growth_rate=0.03,
            debt=0.0,
            cash=0.0,
            diluted_shares_outstanding=10.0,
        )
    with pytest.raises(FinancialModelError, match="greater than zero"):
        generate_sensitivity_table(
            forecast_ufcfs=[100.0],
            base_wacc=0.10,
            base_terminal_growth_rate=0.03,
            debt=0.0,
            cash=0.0,
            diluted_shares_outstanding=0.0,
        )


def test_sensitivity_requires_a_range_divisible_by_its_step() -> None:
    with pytest.raises(FinancialModelError, match="exact multiple"):
        build_rate_grid(0.10, 0.01, 0.006, "WACC")
