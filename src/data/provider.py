"""Provider-neutral financial-data models and interface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

import pandas as pd


class FinancialDataError(RuntimeError):
    """Base exception for errors while obtaining or normalising company data."""


class InvalidTickerError(FinancialDataError):
    """Raised when a ticker is malformed or does not return company data."""


class DataProviderError(FinancialDataError):
    """Raised when the upstream provider cannot fulfil an otherwise valid request."""


@dataclass(frozen=True)
class HistoricalFinancials:
    """Normalised annual financial-statement values in the reporting currency.

    Values other than ``effective_tax_rate`` are currency amounts. ``capex`` is
    normalised to a positive cash outflow. ``change_in_nwc`` is positive when
    working capital increases and therefore consumes cash in the UFCF formula.
    ``net_working_capital`` and ``effective_tax_rate`` are derived fields;
    every other populated value is sourced from a provider statement.
    """

    period_end: date
    revenue: float | None
    operating_income: float | None
    tax_expense: float | None
    pretax_income: float | None
    effective_tax_rate: float | None
    depreciation_and_amortisation: float | None
    capex: float | None
    change_in_nwc: float | None
    current_assets: float | None
    current_liabilities: float | None
    net_working_capital: float | None


@dataclass(frozen=True)
class CompanyFinancials:
    """Company-level market data plus normalised historical statement data."""

    ticker: str
    company_name: str | None
    currency: str | None
    historical_financials: tuple[HistoricalFinancials, ...]
    cash: float | None
    total_debt: float | None
    diluted_shares_outstanding: float | None
    beta: float | None
    market_capitalisation: float | None
    source: str
    retrieved_at: datetime
    missing_fields: tuple[str, ...]

    @property
    def missing_data_message(self) -> str | None:
        """Return an actionable summary when the provider lacks requested fields."""
        if not self.missing_fields:
            return None
        fields = ", ".join(self.missing_fields)
        return f"Unavailable from {self.source}: {fields}. Review or override these assumptions."

    def historical_dataframe(self) -> pd.DataFrame:
        """Return historical statements in a UI-friendly tabular form."""
        return pd.DataFrame(
            [
                {
                    "period_end": period.period_end,
                    "revenue": period.revenue,
                    "operating_income": period.operating_income,
                    "tax_expense": period.tax_expense,
                    "pretax_income": period.pretax_income,
                    "effective_tax_rate": period.effective_tax_rate,
                    "depreciation_and_amortisation": period.depreciation_and_amortisation,
                    "capex": period.capex,
                    "change_in_nwc": period.change_in_nwc,
                    "current_assets": period.current_assets,
                    "current_liabilities": period.current_liabilities,
                    "net_working_capital": period.net_working_capital,
                }
                for period in self.historical_financials
            ]
        )


class FinancialDataProvider(Protocol):
    """Contract implemented by all company-financial-data providers."""

    def get_company_financials(self, ticker: str) -> CompanyFinancials:
        """Retrieve and normalise annual financial data for a public company."""
