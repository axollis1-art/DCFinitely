"""Tests for provider normalisation without live network calls."""

from datetime import date

import pandas as pd
import pytest

from src.data.provider import DataProviderError, InvalidTickerError
from src.data.yfinance_provider import YFinanceProvider


class FakeTicker:
    """A deterministic yfinance-compatible fixture."""

    def __init__(self, *, raise_error: bool = False) -> None:
        self.raise_error = raise_error
        self.periods = [pd.Timestamp("2024-12-31"), pd.Timestamp("2023-12-31")]

    def get_income_stmt(self, *, freq: str) -> pd.DataFrame:
        if self.raise_error:
            raise ConnectionError("provider unavailable")
        return pd.DataFrame(
            {
                self.periods[0]: [120.0, 24.0, 5.0, 25.0],
                self.periods[1]: [100.0, 20.0, 4.0, 20.0],
            },
            index=["Total Revenue", "Operating Income", "Tax Provision", "Pretax Income"],
        )

    def get_cashflow(self, *, freq: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                self.periods[0]: [6.0, -8.0, -3.0],
                self.periods[1]: [5.0, -7.0, -2.0],
            },
            index=["Depreciation And Amortization", "Capital Expenditure", "Change In Working Capital"],
        )

    def get_balance_sheet(self, *, freq: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                self.periods[0]: [60.0, 30.0, 15.0, 40.0],
                self.periods[1]: [50.0, 25.0, 12.0, 35.0],
            },
            index=["Current Assets", "Current Liabilities", "Cash And Cash Equivalents", "Total Debt"],
        )

    def get_info(self) -> dict[str, object]:
        return {
            "longName": "Example Company",
            "currency": "USD",
            "totalCash": 15.0,
            "totalDebt": 40.0,
            "impliedSharesOutstanding": 10.0,
            "beta": 1.1,
            "marketCap": 500.0,
        }


class EmptyIncomeTicker(FakeTicker):
    """A ticker response with no annual statement, as returned for some symbols."""

    def get_income_stmt(self, *, freq: str) -> pd.DataFrame:
        return pd.DataFrame()


def test_provider_normalises_yfinance_statements() -> None:
    provider = YFinanceProvider(ticker_factory=lambda ticker: FakeTicker())

    result = provider.get_company_financials(" example ")

    assert result.ticker == "EXAMPLE"
    assert result.company_name == "Example Company"
    assert result.missing_fields == ()
    assert result.historical_financials[0].period_end == date(2023, 12, 31)
    latest = result.historical_financials[-1]
    assert latest.revenue == 120.0
    assert latest.effective_tax_rate == pytest.approx(0.20)
    assert latest.capex == 8.0
    assert latest.change_in_nwc == 3.0
    assert latest.net_working_capital == 30.0
    assert result.historical_dataframe().shape == (2, 12)


def test_provider_reports_missing_fields_for_manual_review() -> None:
    provider = YFinanceProvider(ticker_factory=lambda ticker: FakeTicker())
    fake = FakeTicker()
    fake.get_info = lambda: {"currency": "USD"}  # type: ignore[method-assign]
    provider = YFinanceProvider(ticker_factory=lambda ticker: fake)

    result = provider.get_company_financials("EXAMPLE")

    assert "beta" in result.missing_fields
    assert "market capitalisation" in result.missing_fields
    assert result.missing_data_message is not None
    assert "override" in result.missing_data_message


def test_provider_rejects_malformed_ticker_before_network_access() -> None:
    calls: list[str] = []
    provider = YFinanceProvider(ticker_factory=lambda ticker: calls.append(ticker) or FakeTicker())

    with pytest.raises(InvalidTickerError, match="valid ticker"):
        provider.get_company_financials("not a ticker!")
    assert calls == []


def test_provider_treats_an_empty_income_statement_as_an_invalid_ticker() -> None:
    provider = YFinanceProvider(ticker_factory=lambda ticker: EmptyIncomeTicker())

    with pytest.raises(InvalidTickerError, match="No annual income statement"):
        provider.get_company_financials("EMPTY")


def test_provider_wraps_upstream_errors() -> None:
    provider = YFinanceProvider(ticker_factory=lambda ticker: FakeTicker(raise_error=True))

    with pytest.raises(DataProviderError, match="Could not retrieve"):
        provider.get_company_financials("EXAMPLE")
