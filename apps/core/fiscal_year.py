"""
Fiscal year utilities for DonorCRM.
Fiscal year: July 1 — June 30 (same as many missionary organizations).
"""
from datetime import date

FISCAL_YEAR_START_MONTH = 7  # July


def fiscal_year_start(today: date) -> date:
    """Return July 1 of the current fiscal year."""
    if today.month >= FISCAL_YEAR_START_MONTH:
        return date(today.year, FISCAL_YEAR_START_MONTH, 1)
    return date(today.year - 1, FISCAL_YEAR_START_MONTH, 1)


def fiscal_year_end(today: date) -> date:
    """Return June 30 of the current fiscal year end."""
    fy_start = fiscal_year_start(today)
    return date(fy_start.year + 1, 6, 30)


def months_elapsed_in_fiscal_year(today: date) -> int:
    """
    Return integer months from July 1 through the current month (inclusive).
    Minimum 1 to prevent division-by-zero.
    Example: April 7, 2026 -> FY started July 1, 2025 -> 10 months (Jul-Apr).
    """
    fy_start = fiscal_year_start(today)
    elapsed = (today.year - fy_start.year) * 12 + (today.month - fy_start.month) + 1
    return max(1, elapsed)


def months_remaining(today: date) -> int:
    """
    Return integer months from today to June 30 of the current FY.
    Minimum 1 to prevent division-by-zero in one-time gift calculations.
    """
    fy_end = fiscal_year_end(today)
    raw = (fy_end.year - today.year) * 12 + (fy_end.month - today.month)
    return max(1, raw)
