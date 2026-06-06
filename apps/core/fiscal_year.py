"""
Fiscal year utilities for DonorCRM.
Fiscal year: June 1 — May 31.

`today` defaults are derived from `timezone.localdate()` rather than
`date.today()`. Today they are equivalent because settings.TIME_ZONE='UTC',
but going through Django's timezone helper means the math stays correct if
TIME_ZONE is ever switched to a US zone (where the FY boundary at midnight
local time would otherwise be off by one day around June 1 / May 31).
"""

from datetime import date

from django.utils import timezone

FISCAL_YEAR_START_MONTH = 6  # June


def fiscal_year_start(today: date) -> date:
    """Return June 1 of the current fiscal year."""
    if today.month >= FISCAL_YEAR_START_MONTH:
        return date(today.year, FISCAL_YEAR_START_MONTH, 1)
    return date(today.year - 1, FISCAL_YEAR_START_MONTH, 1)


def fiscal_year_end(today: date) -> date:
    """Return May 31 of the current fiscal year end."""
    fy_start = fiscal_year_start(today)
    return date(fy_start.year + 1, 5, 31)


def months_elapsed_in_fiscal_year(today: date) -> int:
    """
    Return integer months from June 1 through the current month (inclusive).
    Minimum 1 to prevent division-by-zero.
    Example: April 7, 2026 -> FY started June 1, 2025 -> 11 months (Jun-Apr).
    """
    fy_start = fiscal_year_start(today)
    elapsed = (today.year - fy_start.year) * 12 + (today.month - fy_start.month) + 1
    return max(1, elapsed)


def months_remaining(today: date) -> int:
    """
    Return integer months from today to May 31 of the current FY.
    Minimum 1 to prevent division-by-zero in one-time gift calculations.
    """
    fy_end = fiscal_year_end(today)
    raw = (fy_end.year - today.year) * 12 + (fy_end.month - today.month)
    return max(1, raw)


def get_current_fiscal_year_bounds(reference_date: date | None = None) -> tuple[date, date]:
    """Return (start, end) dates for the fiscal year containing reference_date."""
    today = reference_date or timezone.localdate()
    return fiscal_year_start(today), fiscal_year_end(today)


def get_prior_fiscal_year_bounds(reference_date: date | None = None) -> tuple[date, date]:
    """Return (start, end) dates for the fiscal year immediately prior to the one
    containing reference_date."""
    today = reference_date or timezone.localdate()
    current_start, current_end = get_current_fiscal_year_bounds(today)
    return (
        date(current_start.year - 1, current_start.month, current_start.day),
        date(current_end.year - 1, current_end.month, current_end.day),
    )
