"""
Test stubs for fiscal year utility functions.
FISC-01: fiscal_year_start returns the July 1 start of the fiscal year containing the given date.
FISC-02: months_remaining returns months from current month to end of fiscal year (June), minimum 1.

Imports are deferred inside each test so pytest can collect all 8 items even before
apps/core/fiscal_year.py exists. Tests fail at runtime with ImportError (correct RED state).
"""
from datetime import date

import pytest

# FISC-01: fiscal_year_start boundary cases


def test_fiscal_year_start_august():
    """Aug 15, 2025 is within FY2025-2026 which starts July 1, 2025."""
    from apps.core.fiscal_year import fiscal_year_start

    assert fiscal_year_start(date(2025, 8, 15)) == date(2025, 7, 1)


def test_fiscal_year_start_march():
    """Mar 12, 2026 is within FY2025-2026 which starts July 1, 2025."""
    from apps.core.fiscal_year import fiscal_year_start

    assert fiscal_year_start(date(2026, 3, 12)) == date(2025, 7, 1)


def test_fiscal_year_start_july_1_exact():
    """July 1 is the exact start of a fiscal year — should return itself."""
    from apps.core.fiscal_year import fiscal_year_start

    assert fiscal_year_start(date(2025, 7, 1)) == date(2025, 7, 1)


def test_fiscal_year_start_june_30():
    """June 30, 2025 is the last day of FY2024-2025 which started July 1, 2024."""
    from apps.core.fiscal_year import fiscal_year_start

    assert fiscal_year_start(date(2025, 6, 30)) == date(2024, 7, 1)


# FISC-01 extension: fiscal_year_end


def test_fiscal_year_end_august():
    """Aug 1, 2025 is within FY2025-2026 which ends June 30, 2026."""
    from apps.core.fiscal_year import fiscal_year_end

    assert fiscal_year_end(date(2025, 8, 1)) == date(2026, 6, 30)


# FISC-02: months_remaining boundary cases


def test_months_remaining_normal_month():
    """Aug 15, 2025: months remaining after current month = Sep..Jun = 10 months."""
    from apps.core.fiscal_year import months_remaining

    assert months_remaining(date(2025, 8, 15)) == 10


def test_months_remaining_june_minimum():
    """June 1 — the last month of the fiscal year. Minimum guard returns 1, not 0."""
    from apps.core.fiscal_year import months_remaining

    assert months_remaining(date(2026, 6, 1)) == 1


def test_months_remaining_june_30_minimum():
    """June 30 — last day of fiscal year. Minimum guard returns 1, not 0."""
    from apps.core.fiscal_year import months_remaining

    assert months_remaining(date(2026, 6, 30)) == 1


# FISC-03: get_current_fiscal_year_bounds


def test_current_fiscal_year_bounds_august():
    """Aug 15, 2025 -> FY2025-2026 -> (2025-07-01, 2026-06-30)."""
    from apps.core.fiscal_year import get_current_fiscal_year_bounds

    start, end = get_current_fiscal_year_bounds(date(2025, 8, 15))
    assert start == date(2025, 7, 1)
    assert end == date(2026, 6, 30)


def test_current_fiscal_year_bounds_july_1_exact():
    """July 1 is the exact start — should be the start of its own FY."""
    from apps.core.fiscal_year import get_current_fiscal_year_bounds

    start, end = get_current_fiscal_year_bounds(date(2025, 7, 1))
    assert start == date(2025, 7, 1)
    assert end == date(2026, 6, 30)


def test_current_fiscal_year_bounds_june_30():
    """June 30, 2025 -> prior FY -> (2024-07-01, 2025-06-30)."""
    from apps.core.fiscal_year import get_current_fiscal_year_bounds

    start, end = get_current_fiscal_year_bounds(date(2025, 6, 30))
    assert start == date(2024, 7, 1)
    assert end == date(2025, 6, 30)


def test_current_fiscal_year_bounds_march():
    """Mar 12, 2026 -> FY2025-2026."""
    from apps.core.fiscal_year import get_current_fiscal_year_bounds

    start, end = get_current_fiscal_year_bounds(date(2026, 3, 12))
    assert start == date(2025, 7, 1)
    assert end == date(2026, 6, 30)


def test_current_fiscal_year_bounds_leap_feb_29():
    """Leap-year Feb 29, 2024 -> FY2023-2024 -> (2023-07-01, 2024-06-30)."""
    from apps.core.fiscal_year import get_current_fiscal_year_bounds

    start, end = get_current_fiscal_year_bounds(date(2024, 2, 29))
    assert start == date(2023, 7, 1)
    assert end == date(2024, 6, 30)


def test_current_fiscal_year_bounds_default_is_today():
    """No reference_date defaults to date.today()."""
    from apps.core.fiscal_year import (
        fiscal_year_end,
        fiscal_year_start,
        get_current_fiscal_year_bounds,
    )

    today = date.today()
    start, end = get_current_fiscal_year_bounds()
    assert start == fiscal_year_start(today)
    assert end == fiscal_year_end(today)


# FISC-04: get_prior_fiscal_year_bounds


def test_prior_fiscal_year_bounds_august():
    """Aug 15, 2025 -> prior FY2024-2025 -> (2024-07-01, 2025-06-30)."""
    from apps.core.fiscal_year import get_prior_fiscal_year_bounds

    start, end = get_prior_fiscal_year_bounds(date(2025, 8, 15))
    assert start == date(2024, 7, 1)
    assert end == date(2025, 6, 30)


def test_prior_fiscal_year_bounds_june_30():
    """June 30, 2025 is in FY2024-2025; prior is FY2023-2024 -> (2023-07-01, 2024-06-30)."""
    from apps.core.fiscal_year import get_prior_fiscal_year_bounds

    start, end = get_prior_fiscal_year_bounds(date(2025, 6, 30))
    assert start == date(2023, 7, 1)
    assert end == date(2024, 6, 30)


def test_prior_fiscal_year_bounds_july_1_exact():
    """July 1, 2025 is in FY2025-2026; prior is FY2024-2025."""
    from apps.core.fiscal_year import get_prior_fiscal_year_bounds

    start, end = get_prior_fiscal_year_bounds(date(2025, 7, 1))
    assert start == date(2024, 7, 1)
    assert end == date(2025, 6, 30)
