---
phase: quick-9
plan: 9
subsystem: imports/tests
tags: [tests, spo, csv, fixture, mapping]
dependency_graph:
  requires: [test_data/test_solicitors.csv, test_data/test_gifts.csv, test_data/test_recurring_gifts.csv, test_data/test_constituents.csv]
  provides: [apps/imports/tests/test_spo_csv_fixture_mapping.py]
  affects: [apps.imports.tests]
tech_stack:
  added: []
  patterns: [Django TestCase, fixture file testing, setUp dependency chaining]
key_files:
  created:
    - apps/imports/tests/test_spo_csv_fixture_mapping.py
  modified: []
decisions:
  - "Recurring gifts setUp chains reconcile_missionaries before import_re_constituents — solicitor lookups require Solicitor records, not just User records"
metrics:
  duration: "~6 minutes"
  completed: "2026-03-07"
  tasks_completed: 1
  files_changed: 1
---

# Quick Task 9: SPO CSV Fixture Mapping Tests Summary

**One-liner:** End-to-end fixture tests for all 4 SPO CSV files exercising real headers, Fund Split Amount alias, and solicitor/contact dependency chains.

## What Was Built

Created `apps/imports/tests/test_spo_csv_fixture_mapping.py` with 4 test classes, 9 test methods total. Unlike the synthetic `_make_solicitor_csv` / `_make_gifts_csv` helpers in `test_spo_services.py`, these tests read actual files from disk at `test_data/`.

## Test Classes

| Class | File | Service | Tests |
|-------|------|---------|-------|
| TestSolicitorsFixtureMapping | test_solicitors.csv | reconcile_missionaries | 2 |
| TestGiftsFixtureMapping | test_gifts.csv | import_spo_gifts | 3 |
| TestRecurringGiftsFixtureMapping | test_recurring_gifts.csv | import_re_recurring_gifts | 2 |
| TestConstituentsFixtureMapping | test_constituents.csv | import_re_constituents | 2 |

## Key Results

- All 25 missionaries in test_solicitors.csv created with no errors
- `Fund Split Amount` header alias resolves correctly — amount_cents > 0 for all valid gifts
- Anonymous rows (Gift Is Anonymous = "Yes") imported via anonymous contact
- Recurring gifts: 100/100 created after constituent + missionary prerequisites loaded in setUp
- Constituents: 100 created, type-label row correctly skipped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestRecurringGiftsFixtureMapping setUp missing reconcile_missionaries**

- **Found during:** Task 1 (first test run)
- **Issue:** Plan specified setUp should only import constituents. But `import_re_recurring_gifts` also requires Solicitor records (created by `reconcile_missionaries`) for `RecurringGiftCredit` creation. Without them, each of the 100 gifts added a solicitor-not-found error entry, making `error_count == 100` instead of 0.
- **Fix:** Added `reconcile_missionaries(solicitors_bytes, ...)` call in `TestRecurringGiftsFixtureMapping.setUp` before the constituent import.
- **Files modified:** apps/imports/tests/test_spo_csv_fixture_mapping.py
- **Commit:** 5afedbc

## Verification

```
Ran 83 tests in 108.967s
OK
```

74 existing + 9 new fixture tests. No regressions.

## Self-Check: PASSED

- apps/imports/tests/test_spo_csv_fixture_mapping.py: FOUND
- Commit 5afedbc: FOUND
