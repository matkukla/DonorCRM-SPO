"""Hardening tests for _parse_amount_to_cents (RE/SPO import dollar parser).

Two robustness gaps for malformed import cells:
  - sub-cent values were TRUNCATED (int(Decimal*100)) — money silently lost;
    they must round half-up so a 3-decimal or float-artifact cell is not
    under/over-counted.
  - negative amounts passed straight through to a PositiveBigIntegerField,
    crashing the row with a generic IntegrityError instead of a clean
    per-row "Invalid amount" error. A negative must parse to 0 so the
    caller's existing zero-amount error path fires.

Real RE/SPO exports are 2-decimal, so the common case is unchanged.
"""

import pytest

from apps.imports.re_services import _parse_amount_to_cents


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Common 2-decimal cases unchanged
        ("100.00", 10000),
        ("$1,234.56", 123456),
        ("$100", 10000),
        ("1,234", 123400),
        # Sub-cent rounds half-up (was truncated before)
        ("10.005", 1001),
        ("99.999", 10000),
        ("0.005", 1),
        ("1.004", 100),
        ("1.005", 101),
        # Negative -> 0 (clean "invalid amount" path, not a DB crash)
        ("-50", 0),
        ("-0.01", 0),
        # Garbage / empty -> 0
        ("abc", 0),
        ("", 0),
        ("$", 0),
    ],
)
def test_parse_amount_to_cents(raw, expected):
    assert _parse_amount_to_cents(raw) == expected
