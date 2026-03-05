# Quick Task 8: Fix import feature to accept test CSV files

**Date:** 2026-03-05
**Status:** Completed

## Task

Fix the RE CSV import feature to accept the format used by the test data files
(test_constituents.csv, test_gifts.csv, test_recurring_gifts.csv, test_solicitors.csv).

## Problem

The test CSV files have a leading type-label row (e.g. "Constituent,,,,,") before
the actual column headers. csv.DictReader was reading this label row as the
fieldnames, causing header validation to fail for all four import types.

Additionally, several column names in the test files were not in the header alias maps.

## Solution

1. Added `skip_re_type_label_row()` in `re_services.py` — detects and strips the
   leading RE export type-label row before passing content to csv.DictReader.
2. Added missing header aliases:
   - Constituents: `constituent id`, `organization name`
   - Gifts: `fund split amount` → amount, `solicitor amount` → credit_amount
   - Recurring gifts: `gift id`, `gift date`, `gift installment frequency`,
     `fund id`, `solicitor amount` → amount, `prayer description`
3. Applied `skip_re_type_label_row()` in all four import orchestrators.
