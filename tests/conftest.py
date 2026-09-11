"""Shared fixtures for DCFinitely tests."""

from datetime import UTC, date, datetime

import pytest

from src.data.provider import CompanyFinancials, HistoricalFinancials


@pytest.fixture
def company() -> CompanyFinancials:
    """A complete company record for deterministic workflow and chart tests."""
    return CompanyFinancials(
        ticker="TEST",
        company_name="Test Company",
        currency="USD",
        historical_financials=(
            HistoricalFinancials(date(2023, 12, 31), 100.0, 20.0, 4.0, 20.0, 0.20, 5.0, 7.0, 2.0, 60.0, 30.0, 30.0),
            HistoricalFinancials(date(2024, 12, 31), 110.0, 22.0, 4.4, 22.0, 0.20, 5.5, 7.7, 2.2, 66.0, 33.0, 33.0),
        ),
        cash=15.0,
        total_debt=40.0,
        diluted_shares_outstanding=10.0,
        beta=1.1,
        market_capitalisation=500.0,
        source="Test provider",
        retrieved_at=datetime.now(UTC),
        missing_fields=(),
    )
