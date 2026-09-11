"""Validation helpers shared by the financial model.

The model uses decimal rates: for example, 8% is represented as ``0.08``.
"""

from __future__ import annotations

from math import isfinite


class FinancialModelError(ValueError):
    """Raised when a financial-model input would produce an invalid result."""


def require_finite(value: float, name: str) -> float:
    """Return a finite numeric value or raise a domain-specific error."""
    if not isfinite(value):
        raise FinancialModelError(f"{name} must be a finite number.")
    return value


def require_rate(value: float, name: str, *, minimum: float = 0.0) -> float:
    """Return a valid decimal rate, enforcing a configurable lower bound."""
    require_finite(value, name)
    if value < minimum:
        raise FinancialModelError(f"{name} must be at least {minimum:.2%}.")
    return value


def require_non_negative(value: float, name: str) -> float:
    """Return a non-negative finite value or raise a helpful model error."""
    require_finite(value, name)
    if value < 0:
        raise FinancialModelError(f"{name} cannot be negative.")
    return value
