---
phase: quick-11
plan: 01
subsystem: imports
tags: [bug-fix, spo-import, re-import, payment-type, prayer-intentions, tdd]
dependency_graph:
  requires: [quick-10]
  provides: [payment_type on SPO gifts, prayer intentions from RE recurring gifts]
  affects: [apps/imports/spo_services.py, apps/imports/re_services.py]
tech_stack:
  patterns: [TDD red-green, header alias map, normalize pattern, dedup by (contact_id, text)]
key_files:
  modified:
    - apps/imports/spo_services.py
    - apps/imports/re_services.py
    - apps/imports/tests/test_spo_services.py
    - apps/imports/tests/test_re_services.py
decisions:
  - _normalize_payment_type imported from re_services into spo_services — shared util, no duplication
  - seen_prayers dict initialized outside the per-group loop to dedup across the whole import run
  - Prayer extraction uses inline block (not helper) matching existing SPO pattern
metrics:
  duration: ~10min
  completed: 2026-03-07
  tasks_completed: 3
  files_modified: 4
---

# Quick Task 11: Fix All Bugs Found in 10 Analysis — Summary

**One-liner:** Fixed two confirmed data-loss bugs: SPO gift import now sets `payment_type` via header alias map + `_normalize_payment_type()`, and RE recurring gift import now creates `PrayerIntention` records from `prayer_description` rows with contact-scoped dedup.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing test for SPO payment_type | ad31a61 | test_spo_services.py |
| 1 (GREEN) | Fix payment_type in import_spo_gifts() | 4931017 | spo_services.py |
| 2 (RED) | Failing tests for recurring gift prayers | 61d1570 | test_re_services.py |
| 2 (GREEN) | Extract prayer intentions from recurring gifts | 0b047ba | re_services.py |
| 3 | Full test suite — 84 tests + 9 fixture tests green | (verification) | — |

## Fixes

### Bug 1: SPO gift import never set payment_type

**Root cause:** `_SPO_GIFT_HEADER_ALIASES_NESTED` had no entry for `payment_type`, so "Gift Payment Type" column was never mapped. Even if mapped, `Gift.objects.create()` did not include `payment_type=` argument.

**Fix:**
- Added `'payment_type': ['Gift Payment Type', 'Payment Type', 'payment_type']` to `_SPO_GIFT_HEADER_ALIASES_NESTED`
- Added `_normalize_payment_type` to the import line from `re_services`
- Extracted `payment_type_raw = _get(row, 'payment_type')` and normalized it before `Gift.objects.create()`
- Passed `payment_type=payment_type` to `Gift.objects.create()`

**Test:** `TestImportSpoGifts.test_payment_type_set_on_spo_gift` — EFT maps to `direct_deposit`

### Bug 2: RE recurring gift import silently dropped prayer_description rows

**Root cause:** `import_re_recurring_gifts()` mapped `prayer_description` via `RECURRING_GIFT_HEADER_ALIASES` but never read `first_row.get('prayer_description', '')` or called any prayer creation function.

**Fix:**
- Initialized `seen_prayers: dict = {}` before the outer `try:` block
- After the `RecurringGiftCredit` loop (before `transaction.savepoint_commit(sp)`), added prayer extraction block
- Applies stoplist filter, deduplicates by `(contact.id, normalized_text)`, creates `PrayerIntention` with no Gift M2M link

**Tests:**
- `TestImportRERecurringGiftsPrayers.test_prayer_extracted_from_recurring_gift` — creates 1 PrayerIntention
- `TestImportRERecurringGiftsPrayers.test_no_prayer_when_description_empty` — no PrayerIntention created
- `TestImportRERecurringGiftsPrayers.test_prayer_dedup_across_recurring_gifts` — 2 gifts same text = 1 prayer

## Verification

- All 84 `apps.imports` tests pass (0 failures, 0 errors)
- All 9 SPO CSV fixture mapping tests pass
- No regressions in existing test suite

## Deviations from Plan

None — plan executed exactly as written. The `first_row.get('prayer_description', '')` approach worked correctly because `_group_rows_by_id()` uses `col_map` to store canonical keys in row dicts.

## Self-Check: PASSED

- apps/imports/spo_services.py — modified (payment_type alias + import + field assignment)
- apps/imports/re_services.py — modified (seen_prayers init + prayer extraction block)
- apps/imports/tests/test_spo_services.py — modified (_make_gifts_csv updated + new test)
- apps/imports/tests/test_re_services.py — modified (TestImportRERecurringGiftsPrayers added)
- Commits ad31a61, 4931017, 61d1570, 0b047ba — all verified in git log
