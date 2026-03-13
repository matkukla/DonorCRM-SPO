"""
Test stubs for fiscal year utility functions.
FISC-01: fiscal_year_start returns the July 1 start of the fiscal year containing the given date.
FISC-02: months_remaining returns months from current month to end of fiscal year (June), minimum 1.
"""
import pytest
from datetime import date
from apps.core.fiscal_year import fiscal_year_start, fiscal_year_end, months_remaining


# FISC-01: fiscal_year_start boundary cases


def test_fiscal_year_start_august():
    """Aug 15, 2025 is within FY2025-2026 which starts July 1, 2025."""
    assert fiscal_year_start(date(2025, 8, 15)) == date(2025, 7, 1)


def test_fiscal_year_start_march():
    """Mar 12, 2026 is within FY2025-2026 which starts July 1, 2025."""
    assert fiscal_year_start(date(2026, 3, 12)) == date(2025, 7, 1)


def test_fiscal_year_start_july_1_exact():
    """July 1 is the exact start of a fiscal year — should return itself."""
    assert fiscal_year_start(date(2025, 7, 1)) == date(2025, 7, 1)


def test_fiscal_year_start_june_30():
    """June 30, 2025 is the last day of FY2024-2025 which started July 1, 2024."""
    assert fiscal_year_start(date(2025, 6, 30)) == date(2024, 7, 1)


# FISC-01 extension: fiscal_year_end


def test_fiscal_year_end_august():
    """Aug 1, 2025 is within FY2025-2026 which ends June 30, 2026."""
    assert fiscal_year_end(date(2025, 8, 1)) == date(2026, 6, 30)


# FISC-02: months_remaining boundary cases


def test_months_remaining_normal_month():
    """Aug 15, 2025: months remaining = Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Apr, May, Jun = 11.

    Wait — the plan spec says 10 (Aug to June = 10 months). That means August itself is
    the current month and we count from the NEXT month: Sep..Jun = 10. Using that interpretation.
    """
    assert months_remaining(date(2025, 8, 15)) == 10


def test_months_remaining_june_minimum():
    """June 1 — the last month of the fiscal year. Minimum guard returns 1, not 0."""
    assert months_remaining(date(2026, 6, 1)) == 1


def test_months_remaining_june_30_minimum():
    """June 30 — last day of fiscal year. Minimum guard returns 1, not 0."""
    assert months_remaining(date(2026, 6, 30)) == 1
