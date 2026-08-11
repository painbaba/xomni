"""Tiny arithmetic helpers for the verify-runner example project."""

from __future__ import annotations


def add(a: float, b: float) -> float:
    """Return the sum of ``a`` and ``b``."""
    return a + b


def is_even(n: int) -> bool:
    """Return True when ``n`` is even."""
    return n % 2 == 0
