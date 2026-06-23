"""Regression tests for the 2026-06-22 report_3 re-scan finding #9.

`sanitize_cell_value` stripped leading formula-injection characters with a
`value = value[1:]` loop, which allocates a new string every iteration — O(n^2)
on a long run of leading formula chars (CWE-400, admin MPD upload). It is now a
single-pass `str.lstrip`. These tests pin BOTH the behavior (same chars
stripped) and the performance (linear, not quadratic).

The perf test fails if the quadratic slicing loop is reintroduced: a 200k-char
leading-formula string takes microseconds under lstrip but tens of seconds under
the old O(n^2) loop, so the generous 1.0s bound cleanly distinguishes them.
"""

import time

import pytest

from apps.imports.mpd_services import FORMULA_INJECTION_CHARS, sanitize_cell_value


class TestSanitizeBehavior:
    @pytest.mark.parametrize("ch", sorted(FORMULA_INJECTION_CHARS))
    def test_strips_each_leading_formula_char(self, ch):
        assert sanitize_cell_value(f"{ch}HYPERLINK(...)") == "HYPERLINK(...)"

    def test_strips_a_run_of_mixed_leading_chars(self):
        assert sanitize_cell_value("=+@\t\r=SUM(A1)") == "SUM(A1)"

    def test_preserves_leading_minus_for_negative_currency(self):
        # '-' is intentionally NOT a formula-injection char (negative currency).
        assert sanitize_cell_value("-$468.33") == "-$468.33"

    def test_preserves_interior_and_trailing_chars(self):
        assert sanitize_cell_value("Acme=Corp") == "Acme=Corp"
        assert sanitize_cell_value("plain value") == "plain value"

    def test_non_string_and_empty_passthrough(self):
        assert sanitize_cell_value(None) is None
        assert sanitize_cell_value(1234) == 1234
        assert sanitize_cell_value("") == ""


class TestSanitizeIsLinear:
    def test_long_formula_prefix_is_fast(self):
        payload = ("=" * 200_000) + "SUM(A1)"
        start = time.perf_counter()
        result = sanitize_cell_value(payload)
        elapsed = time.perf_counter() - start
        assert result == "SUM(A1)"
        # Linear lstrip: sub-millisecond. Old O(n^2) loop: tens of seconds.
        assert elapsed < 1.0, f"sanitize_cell_value took {elapsed:.3f}s — quadratic regression?"
