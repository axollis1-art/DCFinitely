"""Yahoo Finance-backed implementation of the financial-data provider interface."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
import re
from typing import Any

import pandas as pd

from src.data.provider import (
    CompanyFinancials,
    DataProviderError,
    HistoricalFinancials,
    InvalidTickerError,
)


TickerFactory = Callable[[str], Any]
_TICKER_PATTERN = re.compile(r"^[A-Za-z0-9.^=-]{1,20}$")


class YFinanceProvider:
    """Retrieve public company fundamentals from Yahoo Finance via yfinance.

    yfinance exposes reporting-statement labels that can differ by company and
    accounting standard. This adapter normalises known label variants, preserves
    missing values as ``None``, and reports them in ``missing_fields`` rather
    than substituting assumptions.
    """

    source_name = "Yahoo Finance via yfinance"

    def __init__(self, ticker_factory: TickerFactory | None = None) -> None:
        if ticker_factory is None:
            try:
                import yfinance as yf
            except ImportError as error:  # pragma: no cover - dependency configuration failure
                raise DataProviderError(
                    "yfinance is not installed. Install the project requirements first."
                ) from error
            ticker_factory = yf.Ticker
        self._ticker_factory = ticker_factory

    def get_company_financials(self, ticker: str) -> CompanyFinancials:
        """Fetch annual statements and market inputs for ``ticker``.

        No credentials are needed. Invalid symbols, empty statement responses,
        and upstream exceptions are converted into domain-specific errors that
        the UI can render without exposing a traceback.
        """
        symbol = self._normalise_ticker(ticker)
        try:
            company = self._ticker_factory(symbol)
            income_statement = company.get_income_stmt(freq="yearly")
            cash_flow = company.get_cashflow(freq="yearly")
            balance_sheet = company.get_balance_sheet(freq="yearly")
            info = company.get_info()
        except Exception as error:
            raise DataProviderError(
                f"Could not retrieve financial data for {symbol}. Please try again later."
            ) from error

        if not isinstance(income_statement, pd.DataFrame) or income_statement.empty:
            raise InvalidTickerError(
                f"No annual income statement was found for {symbol}. Check the ticker and try again."
            )
        if not isinstance(cash_flow, pd.DataFrame):
            cash_flow = pd.DataFrame()
        if not isinstance(balance_sheet, pd.DataFrame):
            balance_sheet = pd.DataFrame()
        if not isinstance(info, dict):
            info = {}

        historical = self._build_historical_financials(income_statement, cash_flow, balance_sheet)
        latest_period = historical[-1] if historical else None
        latest_balance_period = balance_sheet.columns[0] if not balance_sheet.empty else None
        cash = self._first_present(
            self._as_number(info.get("totalCash")),
            self._statement_value(
                balance_sheet,
                (
                    "Cash Cash Equivalents And Short Term Investments",
                    "Cash And Cash Equivalents",
                    "CashCashEquivalentsAndShortTermInvestments",
                    "CashAndCashEquivalents",
                ),
                latest_balance_period,
            ) if latest_balance_period is not None else None,
        )
        total_debt = self._first_present(
            self._as_number(info.get("totalDebt")),
            self._statement_value(balance_sheet, ("Total Debt", "TotalDebt"), latest_balance_period)
            if latest_balance_period is not None
            else None,
        )
        diluted_shares = self._first_present(
            self._as_number(info.get("impliedSharesOutstanding")),
            self._as_number(info.get("sharesOutstanding")),
        )
        beta = self._as_number(info.get("beta"))
        market_capitalisation = self._as_number(info.get("marketCap"))
        missing_fields = self._missing_fields(
            latest_period,
            cash=cash,
            total_debt=total_debt,
            diluted_shares=diluted_shares,
            beta=beta,
            market_capitalisation=market_capitalisation,
        )
        return CompanyFinancials(
            ticker=symbol,
            company_name=self._as_text(info.get("longName") or info.get("shortName")),
            currency=self._as_text(info.get("currency")),
            historical_financials=historical,
            cash=cash,
            total_debt=total_debt,
            diluted_shares_outstanding=diluted_shares,
            beta=beta,
            market_capitalisation=market_capitalisation,
            source=self.source_name,
            retrieved_at=datetime.now(UTC),
            missing_fields=tuple(missing_fields),
        )

    @staticmethod
    def _normalise_ticker(ticker: str) -> str:
        symbol = ticker.strip().upper() if isinstance(ticker, str) else ""
        if not _TICKER_PATTERN.fullmatch(symbol):
            raise InvalidTickerError("Enter a valid ticker symbol, for example AAPL or BRK-B.")
        return symbol

    def _build_historical_financials(
        self,
        income_statement: pd.DataFrame,
        cash_flow: pd.DataFrame,
        balance_sheet: pd.DataFrame,
    ) -> tuple[HistoricalFinancials, ...]:
        periods = sorted((period for period in income_statement.columns if self._to_date(period)), key=self._to_date)
        records: list[HistoricalFinancials] = []
        for period in periods:
            period_end = self._to_date(period)
            if period_end is None:
                continue
            revenue = self._statement_value(
                income_statement,
                ("Total Revenue", "Operating Revenue", "TotalRevenue", "OperatingRevenue"),
                period,
            )
            operating_income = self._statement_value(
                income_statement,
                ("Operating Income", "EBIT", "OperatingIncome", "TotalOperatingIncomeAsReported"),
                period,
            )
            tax_expense = self._absolute_value(
                self._statement_value(income_statement, ("Tax Provision", "Tax Expense", "TaxProvision"), period)
            )
            pretax_income = self._statement_value(
                income_statement, ("Pretax Income", "Pre Tax Income", "PretaxIncome"), period
            )
            effective_tax_rate = (
                tax_expense / abs(pretax_income)
                if tax_expense is not None and pretax_income not in (None, 0)
                else None
            )
            depreciation_and_amortisation = self._absolute_value(
                self._statement_value(
                    cash_flow,
                    (
                        "Depreciation And Amortization",
                        "Depreciation And Amortisation",
                        "Depreciation",
                        "DepreciationAndAmortization",
                        "DepreciationAmortizationDepletion",
                    ),
                    period,
                )
            )
            capex = self._absolute_value(
                self._statement_value(cash_flow, ("Capital Expenditure", "Capital Expenditures", "CapitalExpenditure"), period)
            )
            cash_flow_change_in_nwc = self._statement_value(
                cash_flow,
                (
                    "Change In Working Capital",
                    "Change In Other Working Capital",
                    "ChangeInWorkingCapital",
                    "ChangeInOtherWorkingCapital",
                ),
                period,
            )
            current_assets = self._statement_value(
                balance_sheet, ("Current Assets", "Total Current Assets", "CurrentAssets"), period
            )
            current_liabilities = self._statement_value(
                balance_sheet, ("Current Liabilities", "Total Current Liabilities", "CurrentLiabilities"), period
            )
            net_working_capital = (
                current_assets - current_liabilities
                if current_assets is not None and current_liabilities is not None
                else None
            )
            records.append(
                HistoricalFinancials(
                    period_end=period_end,
                    revenue=revenue,
                    operating_income=operating_income,
                    tax_expense=tax_expense,
                    pretax_income=pretax_income,
                    effective_tax_rate=effective_tax_rate,
                    depreciation_and_amortisation=depreciation_and_amortisation,
                    capex=capex,
                    change_in_nwc=(
                        -cash_flow_change_in_nwc if cash_flow_change_in_nwc is not None else None
                    ),
                    current_assets=current_assets,
                    current_liabilities=current_liabilities,
                    net_working_capital=net_working_capital,
                )
            )
        return tuple(records)

    @staticmethod
    def _statement_value(frame: pd.DataFrame, labels: Iterable[str], period: Any) -> float | None:
        if frame.empty or period not in frame.columns:
            return None
        for label in labels:
            if label in frame.index:
                return YFinanceProvider._as_number(frame.at[label, period])
        return None

    @staticmethod
    def _as_number(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_text(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _absolute_value(value: float | None) -> float | None:
        return abs(value) if value is not None else None

    @staticmethod
    def _first_present(*values: float | None | bool) -> float | None:
        for value in values:
            if isinstance(value, (float, int)):
                return float(value)
        return None

    @staticmethod
    def _to_date(period: Any) -> date | None:
        try:
            return pd.Timestamp(period).date()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _missing_fields(
        latest: HistoricalFinancials | None,
        *,
        cash: float | None,
        total_debt: float | None,
        diluted_shares: float | None,
        beta: float | None,
        market_capitalisation: float | None,
    ) -> list[str]:
        fields: dict[str, Any] = {
            "revenue": latest and latest.revenue,
            "operating income": latest and latest.operating_income,
            "tax rate": latest and latest.effective_tax_rate,
            "depreciation and amortisation": latest and latest.depreciation_and_amortisation,
            "capex": latest and latest.capex,
            "working capital": latest and latest.net_working_capital,
            "cash": cash,
            "debt": total_debt,
            "diluted shares outstanding": diluted_shares,
            "beta": beta,
            "market capitalisation": market_capitalisation,
        }
        if latest is None:
            return list(fields)
        return [field for field, value in fields.items() if value is None]
