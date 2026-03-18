---
phase: quick
plan: gc8
subsystem: imports/test-data
tags: [imports, csv, test-fixtures, mapping-audit]
dependency_graph:
  requires: []
  provides: [verified-test-fixtures, passing-fixture-mapping-tests]
  affects: [apps/imports/tests/test_spo_csv_fixture_mapping.py]
tech_stack:
  added: []
  patterns: [fixture-mapping-tests, csv-header-alias-maps]
key_files:
  modified:
    - apps/imports/tests/test_spo_csv_fixture_mapping.py
decisions:
  - All 9 fixture mapping tests now pass; test expectations updated to match actual CSV row counts
  - TestGiftsFixtureMapping.setUp() now imports constituents (required because all gift constituent IDs reference test_constituents.csv)
  - test_gifts_anonymous_rows_imported renamed to test_gifts_all_rows_imported_via_named_contacts (no anonymous rows in test data)
metrics:
  duration: "~4 min"
  completed_date: "2026-03-18"
  tasks_completed: 1
  files_modified: 1
---

# Phase quick Plan gc8: Check All Test Data Files — Summary

**One-liner:** All 5 test_data CSVs confirmed to map correctly through the import pipeline; 7 test fixture-count mismatches fixed, all 9 tests now pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Run existing fixture mapping tests and analyze results | 878aec4 | apps/imports/tests/test_spo_csv_fixture_mapping.py |

## Mapping Analysis — All 5 CSV Files

### 1. test_solicitors.csv

- **Rows:** 20 data rows (1 type-label "Solicitor" + 1 header + 20 data rows)
- **Import function:** `reconcile_missionaries()` in `apps/imports/spo_services.py`
- **Column mapping:**

| CSV Column | Canonical | Model Field |
|------------|-----------|-------------|
| `Name` | `raw_name` via `SOLICITOR_HEADER_ALIASES['name']` | User.first_name + User.last_name (parsed) |

- **Intentionally ignored columns:** None (only one data column: `Name`)
- **Edge cases:** All names are "First Last" format; `normalize_solicitor_name()` reverses to "last, first" for matching
- **Result:** 20 missionaries auto-created, 20 Solicitor records created

### 2. test_constituents.csv

- **Rows:** 400 data rows (1 type-label "Constituent" + 1 header + 400 data rows)
- **Import function:** `import_re_constituents()` in `apps/imports/re_services.py`
- **Column mapping via `CONSTITUENT_HEADER_ALIASES`:**

| CSV Column | Canonical | Model Field |
|------------|-----------|-------------|
| `Constituent ID` | `constituent_id` | Contact.external_constituent_id |
| `First Name` | `first_name` | Contact.first_name |
| `Last Name` | `last_name` | Contact.last_name |
| `Organization Name` | `organization_name` | Contact.organization_name |
| `Address Line 1` | `street_address` | Contact.street_address |
| `City` | `city` | Contact.city |
| `State` | `state` | Contact.state |
| `ZIP` | `postal_code` | Contact.postal_code |
| `Country` | `country` | Contact.country |
| `Phone` | `phone` | Contact.phone |
| `Email` | `email` | Contact.email |

- **Intentionally ignored columns:**
  - `Constituent Date Last Changed` — metadata timestamp, not in `CONSTITUENT_HEADER_ALIASES`; not stored (no model field needed)
  - `Address Line 2` — not in `CONSTITUENT_HEADER_ALIASES`; Contact model has no `address_line_2` field (intentional: RE export sometimes has it, but the model doesn't track secondary address lines)
- **Result:** 400 contacts created, 0 errors

### 3. test_gifts.csv

- **Rows:** 100 data rows (1 type-label "Gift" + 1 header + 100 data rows)
- **Import function:** `import_spo_gifts()` in `apps/imports/spo_services.py`
- **Column mapping via `SPO_GIFT_HEADER_ALIAS_MAP`:**

| CSV Column | Canonical | Model Field |
|------------|-----------|-------------|
| `Gift ID` | `gift_id` | Gift.external_gift_id |
| `Gift Date` | `gift_date` | Gift.gift_date |
| `Fund Split Amount` | `gift_amount` | Gift.amount_cents (via `_parse_amount_to_cents`) |
| `Constituent ID` | `constituent_id` | Contact lookup (external_constituent_id) |
| `Gift Is Anonymous` | `is_anonymous` | Contact routing logic |
| `Solicitor Name` | `solicitor_name` | Solicitor/User lookup |
| `Solicitor Amount` | `solicitor_amount` | GiftCredit.amount_cents |
| `Gift Payment Type` | `payment_type` | Gift.payment_type |
| `Gift Specific Attributes Prayer Requests Description` | `prayer_description` | PrayerIntention.description |

- **Intentionally ignored columns:**
  - `Gift Date Last Changed` — metadata, not in any alias map
  - `Gift Type` — always "Cash" in test data; not stored on Gift model
  - `Soft Credit Recipient ID` — RE-specific soft credit tracking; not used in DonorCRM model
  - `Fund ID` — fund name used only for routing, not stored directly on Gift (no Fund lookup in SPO path)
- **Edge cases:**
  - `Fund Split Amount` uses dollar-formatted values like `$500.00`; `_parse_amount_to_cents()` strips `$` and commas correctly
  - All 100 rows have `Gift Is Anonymous = No`; all constituent IDs resolve to contacts in test_constituents.csv
  - 6 gifts have prayer descriptions; these create `PrayerIntention` records
- **Result:** 100 gifts created, 0 errors

### 4. test_recurring_gifts.csv

- **Rows:** 300 data rows (1 type-label "Recurring Gift" + 1 header + 300 data rows)
- **Import function:** `import_re_recurring_gifts()` in `apps/imports/re_services.py`
- **Column mapping via `RECURRING_GIFT_HEADER_ALIASES`:**

| CSV Column | Canonical | Model Field |
|------------|-----------|-------------|
| `Gift ID` | `gift_id` | RecurringGift.external_gift_id |
| `Gift Date` | `start_date` | RecurringGift.start_date |
| `Gift Installment Frequency` | `frequency` | RecurringGift.frequency (via `FREQUENCY_MAP`) |
| `Fund ID` | `fund` | RecurringGift.fund |
| `Constituent ID` | `constituent_id` | Contact lookup |
| `Gift Is Anonymous` | (via is_anonymous routing) | Contact routing |
| `Solicitor Name` | `solicitor_name` | Solicitor/User lookup + RecurringGiftCredit |
| `Solicitor Amount` | `amount` | RecurringGift.amount_cents (via `_parse_amount_to_cents`) |
| `Gift Payment Type` | (payment_type) | RecurringGift.payment_type |
| `Gift Status` | `status` | RecurringGift.status (via `STATUS_MAP`) |
| `Gift Specific Attributes Prayer Requests Description` | `prayer_description` | PrayerIntention.description |

- **Intentionally ignored columns:**
  - `Gift Date Last Changed` — metadata
  - `Gift Type` — always "Recurring Gift"; not stored
  - `Gift First Installment Due` — schedule metadata, not in alias map
  - `Last Installment/Payment Date Due` — end date (maps to `end_date` via `end date` alias)
  - `Number of Installments Scheduled` — schedule metadata
  - `Gift First Installment Due_1` — duplicate/extra RE export column
  - `Gift Status Date` — status change timestamp, not stored
  - `Soft Credit Recipient ID` — not used
- **Edge cases:**
  - `Solicitor Amount` maps to `amount` canonical via `'solicitor amount': 'amount'` alias
  - Dollar-formatted `$50.00` etc. parsed correctly by `_parse_amount_to_cents()`
  - All 300 rows use `frequency = Monthly` → maps to `RecurringGiftFrequency.MONTHLY`
  - All 300 rows have `status = Active` → maps to `RecurringGiftStatus.ACTIVE`
- **Result:** 300 recurring gifts created, 0 errors

### 5. test_smartsheet.csv

- **Rows:** 20 data rows (1 header only, no type-label row)
- **Import function:** `process_mpd_upload()` in `apps/imports/mpd_services.py`
- **All 23 columns recognized by `SMARTSHEET_COLUMN_MAP`:**

| CSV Column | Mapped To |
|------------|-----------|
| `Full Name` | `None` (skip — derived from First + Last) |
| `First Name` | `_first_name` (matching key) |
| `Last Name` | `_last_name` (matching key) |
| `Active Recurring Gifts` | `active_recurring_gifts` (currency) |
| `Annual Gifts` | `annual_gifts` (currency) |
| `Monthly Average` | `monthly_average` (currency) |
| `Annual MPD Estimate` | `annual_mpd_estimate` (currency) |
| `MPD Standard` | `mpd_standard` (currency) |
| `$ Amount Below MPD Standard` | `amount_below_mpd_standard` (currency) |
| `% Standard to Max` | `pct_standard_to_max` (percentage) |
| `Met MPD Standard` | `met_mpd_standard` (boolean) |
| `MPD Maximum` | `mpd_maximum` (currency) |
| `Met MAXIMUM` | `met_maximum` (boolean) |
| `Amount Above/Below Maximum` | `amount_above_below_maximum` (currency) |
| `Match Met` | `match_met` (boolean) |
| `Match Met for Rest of Fiscal Year (Based on RFB)` | `match_met_rest_fy` (boolean) |
| `Latest Roll Forward Balance` | `latest_roll_forward_balance` (currency) |
| `Current MPD Cap` | `current_mpd_cap` (currency) |
| `Months Remaining in RF` | `months_remaining_rf` (special string) |
| `Proj. Monthly Deduction from RFB (Cap - Rec.Gifts)` | `proj_monthly_deduction_rfb` (currency) |
| `PAY FORECAST Over 12 Months` | `pay_forecast_12_months` (currency) |
| `Pay Forecast Over Fiscal Year` | `pay_forecast_over_fy` (currency) |
| `Total One-Time Gifts - April` | `total_one_time_gifts_april` (currency) |

- **Edge cases:**
  - `% Standard to Max` column contains decimal values like `2.919822` (not `291%` format). `parse_percentage()` detects `abs(value) <= 10` and multiplies by 100 → returns `292`. This is the intended behavior for XLSX float percentages (CSV exports them as the raw float, not the display percentage).
  - Boolean columns (`Met MPD Standard`, `Met MAXIMUM`, `Match Met`, `Match Met for Rest of Fiscal Year`) contain "Yes"/"No" strings → correctly parsed to `True`/`False` by `parse_yes_no()`
  - All monetary columns handle dollar-formatted strings via `parse_currency()`
  - `Months Remaining in RF` values like `17.675859` are formatted as decimal strings (trailing zeros stripped)
- **Result:** All 23 columns fully recognized, no unrecognized columns

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertions referenced wrong row counts for 3 fixture files**

- **Found during:** Task 1 — initial test run showed 7 test failures
- **Issue:** Test file comment and assertions were written for an earlier version of the test data files that had fewer rows. Current files: test_solicitors.csv = 20 rows (not 25), test_recurring_gifts.csv = 300 rows (not 100), test_constituents.csv = 400 rows. The test for recurring gifts asserted 100.
- **Fix:** Updated all count assertions to match actual file contents (25→20 for solicitors, 100→300 for recurring gifts)
- **Files modified:** `apps/imports/tests/test_spo_csv_fixture_mapping.py`
- **Commit:** 878aec4

**2. [Rule 1 - Bug] TestGiftsFixtureMapping.setUp() missing constituent import**

- **Found during:** Task 1 — all 3 gift tests failed with created_count=0 because contacts not found
- **Issue:** Gift rows reference constituent IDs from test_constituents.csv, but setUp() only called `reconcile_missionaries()`. Without the constituent import, `Contact.objects.filter(external_constituent_id=...)` returns None for all 100 rows, causing 100 skipped gifts.
- **Fix:** Added `import_re_constituents()` call to setUp(), importing all 400 contacts before gift import
- **Files modified:** `apps/imports/tests/test_spo_csv_fixture_mapping.py`
- **Commit:** 878aec4

**3. [Rule 1 - Bug] test_gifts_anonymous_rows_imported tested non-existent data**

- **Found during:** Task 1 — all 100 gifts have `Gift Is Anonymous = No`; the test asserted an Anonymous Donor contact would be created
- **Issue:** Test assumed anonymous gift rows existed in the fixture; none do. Checking the data: `cut -d',' -f8 test_gifts.csv | sort | uniq -c` shows all 100 data rows have "No" in the anonymous column.
- **Fix:** Renamed test to `test_gifts_all_rows_imported_via_named_contacts` and updated assertions to verify all 100 gifts are created via named contacts
- **Files modified:** `apps/imports/tests/test_spo_csv_fixture_mapping.py`
- **Commit:** 878aec4

## Verification Results

All 9 tests pass:

```
Ran 9 tests in 194.232s
OK
```

| Test | Result |
|------|--------|
| TestConstituentsFixtureMapping.test_constituents_type_label_row_skipped | PASS |
| TestConstituentsFixtureMapping.test_import_constituents_with_fixture | PASS |
| TestGiftsFixtureMapping.test_gifts_all_rows_imported_via_named_contacts | PASS |
| TestGiftsFixtureMapping.test_gifts_fund_split_amount_header_resolves | PASS |
| TestGiftsFixtureMapping.test_import_spo_gifts_with_fixture | PASS |
| TestRecurringGiftsFixtureMapping.test_import_recurring_gifts_with_fixture | PASS |
| TestRecurringGiftsFixtureMapping.test_recurring_gifts_type_label_row_skipped | PASS |
| TestSolicitorsFixtureMapping.test_reconcile_missionaries_with_fixture | PASS |
| TestSolicitorsFixtureMapping.test_reconcile_creates_solicitor_records | PASS |

## Self-Check: PASSED

- Commit 878aec4 exists: confirmed
- Test file modified: `apps/imports/tests/test_spo_csv_fixture_mapping.py` confirmed modified
- All 9 tests pass as shown in final test run output
