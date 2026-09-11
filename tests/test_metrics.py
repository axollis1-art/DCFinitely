"""Tests for transparent free-cash-flow calculations."""

import pytest

from src.financials.metrics import calculate_ufcf


def test_calculate_ufcf() -> None:
    assert calculate_ufcf(100.0, 0.25, 20.0, 30.0, 10.0) == pytest.approx(55.0)


def test_calculate_ufcf_allows_working_capital_release() -> None:
    assert calculate_ufcf(100.0, 0.25, 20.0, 30.0, -10.0) == pytest.approx(75.0)


def test_calculate_ufcf_rejects_tax_rate_above_100_percent() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        calculate_ufcf(100.0, 1.01, 20.0, 30.0, 10.0)
