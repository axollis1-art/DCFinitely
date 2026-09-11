"""Pure WACC and terminal-growth sensitivity analysis for DCF valuations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from collections.abc import Sequence

import pandas as pd

from src.utils.validation import FinancialModelError, require_finite, require_non_negative, require_rate
from src.valuation.dcf import calculate_dcf_valuation


@dataclass(frozen=True)
class SensitivityTable:
    """Implied-share-price results across WACC and terminal-growth scenarios.

    A ``None`` price marks an invalid Gordon Growth combination where WACC is
    less than or equal to terminal growth. The table contains no presentation
    framework dependency and can therefore be tested independently of Streamlit.
    """

    wacc_rates: tuple[float, ...]
    terminal_growth_rates: tuple[float, ...]
    implied_share_prices: tuple[tuple[float | None, ...], ...]
    base_wacc_index: int
    base_terminal_growth_index: int

    @property
    def base_case_price(self) -> float | None:
        """Return the price at the central/base-case assumptions."""
        return self.implied_share_prices[self.base_wacc_index][self.base_terminal_growth_index]

    def to_dataframe(self) -> pd.DataFrame:
        """Return a numeric table with WACC as rows and growth rates as columns."""
        return pd.DataFrame(
            self.implied_share_prices,
            index=pd.Index(self.wacc_rates, name="WACC"),
            columns=pd.Index(self.terminal_growth_rates, name="Terminal growth"),
            dtype=float,
        )


def build_rate_grid(base_rate: float, half_range: float, step: float, name: str) -> tuple[float, ...]:
    """Build an evenly spaced, base-case-centred decimal-rate grid.

    ``half_range`` must be an exact multiple of ``step`` so a user cannot
    inadvertently create a grid that omits the requested boundary or base case.
    """
    require_rate(base_rate, name, minimum=-1.0)
    require_non_negative(half_range, f"{name} range")
    require_finite(step, f"{name} step")
    if step <= 0:
        raise FinancialModelError(f"{name} step must be greater than zero.")
    steps = half_range / step
    rounded_steps = round(steps)
    if not isclose(steps, rounded_steps, rel_tol=0.0, abs_tol=1e-9):
        raise FinancialModelError(f"{name} range must be an exact multiple of its step.")
    return tuple(round(base_rate + offset * step, 10) for offset in range(-rounded_steps, rounded_steps + 1))


def generate_sensitivity_table(
    *,
    forecast_ufcfs: Sequence[float],
    base_wacc: float,
    base_terminal_growth_rate: float,
    debt: float,
    cash: float,
    diluted_shares_outstanding: float,
    wacc_half_range: float = 0.01,
    wacc_step: float = 0.005,
    terminal_growth_half_range: float = 0.005,
    terminal_growth_step: float = 0.0025,
) -> SensitivityTable:
    """Calculate an implied-share-price matrix around the base DCF case.

    The existing valuation bridge calculates every valid cell, preserving one
    source of truth for terminal value, discounting, debt, cash, and shares.
    Invalid Gordon Growth pairs are represented by ``None`` instead of a
    misleading numerical output.
    """
    require_non_negative(debt, "Debt")
    require_non_negative(cash, "Cash")
    shares = require_non_negative(diluted_shares_outstanding, "Diluted shares outstanding")
    if shares == 0:
        raise FinancialModelError("Diluted shares outstanding must be greater than zero.")
    if not forecast_ufcfs:
        raise FinancialModelError("At least one forecast UFCF is required.")

    wacc_rates = build_rate_grid(base_wacc, wacc_half_range, wacc_step, "WACC")
    growth_rates = build_rate_grid(
        base_terminal_growth_rate,
        terminal_growth_half_range,
        terminal_growth_step,
        "Terminal growth rate",
    )
    if base_wacc <= base_terminal_growth_rate:
        raise FinancialModelError("Base-case WACC must be greater than the terminal growth rate.")

    prices: list[tuple[float | None, ...]] = []
    for wacc in wacc_rates:
        row: list[float | None] = []
        for growth_rate in growth_rates:
            if wacc <= growth_rate:
                row.append(None)
                continue
            valuation = calculate_dcf_valuation(
                forecast_ufcfs=forecast_ufcfs,
                wacc=wacc,
                terminal_growth_rate=growth_rate,
                debt=debt,
                cash=cash,
                diluted_shares_outstanding=shares,
            )
            row.append(valuation.implied_share_price)
        prices.append(tuple(row))

    return SensitivityTable(
        wacc_rates=wacc_rates,
        terminal_growth_rates=growth_rates,
        implied_share_prices=tuple(prices),
        base_wacc_index=wacc_rates.index(round(base_wacc, 10)),
        base_terminal_growth_index=growth_rates.index(round(base_terminal_growth_rate, 10)),
    )
