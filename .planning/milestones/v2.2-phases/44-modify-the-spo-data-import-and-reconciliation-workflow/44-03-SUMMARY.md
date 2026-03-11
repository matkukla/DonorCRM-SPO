---
phase: 44-modify-the-spo-data-import-and-reconciliation-workflow
plan: "03"
subsystem: imports
tags: [spo, gifts, prayer, import, gift-credit, tdd]
dependency_graph:
  requires:
    - 44-02  # reconcile_missionaries() creates Solicitor records used here
  provides:
    - import_spo_gifts()  # Step 2 of SPO pipeline
    - import_spo_prayers()  # Step 3 of SPO pipeline
  affects:
    - apps/gifts/models.Gift
    - apps/gifts/models.GiftCredit
    - apps/prayers/models.PrayerIntention
tech_stack:
  patterns:
    - TDD (red → green, two-task cycle)
    - Per-row savepoint isolation for gift import errors
    - SHA256 dedup with force=True bypass (separate ImportBatchType per function)
    - Flat alias map (SPO_GIFT_HEADER_ALIAS_MAP) built from nested dict for _build_header_mapping()
key_files:
  modified:
    - apps/imports/spo_services.py
    - apps/imports/tests/test_spo_services.py
decisions:
  - import_spo_prayers() uses SPO_PRAYER dedup namespace separate from SPO_GIFT — allows re-running prayer extraction without reimporting gifts
  - _maybe_create_prayer_intention() called with (gift, prayer_text, contact, seen_prayers) — reuses existing RE service function directly
  - When Solicitor not found in pre-built lookup (edge case), _get_or_create_missionary_solicitor() called as fallback
  - Prayer-only import (no existing Gift) uses inline prayer creation logic duplicated from re_services PRAYER_STOPLIST pattern
metrics:
  duration: "~8 minutes"
  completed: "2026-03-07"
  tasks_completed: 2
  files_modified: 2
---

# Phase 44 Plan 03: SPO Gift and Prayer Import Summary

**One-liner:** `import_spo_gifts()` with three-path contact resolution, GiftCredit attribution, prayer extraction, and savepoint isolation; `import_spo_prayers()` for prayer-only rerun pass.

## What Was Built

### Task 1: import_spo_gifts() — TDD

**RED:** Added failing tests for `TestImportSpoGifts`:
- `test_blank_constituent_id_treated_as_anonymous` — blank constituent_id → anonymous contact
- `test_unresolved_solicitor_gift_skipped` — unknown solicitor name → skip + count in summary
- `test_gift_attributed_to_missionary` — Gift + GiftCredit linked to missionary's Solicitor
- `test_prayer_extracted_from_gift_description` — prayer_description column → PrayerIntention
- `test_dedup_same_file` — same file bytes → DUPLICATE status
- `test_type_label_row_skipped` — leading "Gift" type-label row stripped by skip_re_type_label_row

**GREEN:** Implemented `import_spo_gifts()` in `apps/imports/spo_services.py`:
1. SHA256 dedup check (SPO_GIFT type, force=True deletes existing batch)
2. CSV decode + type-label row skip
3. Header mapping via `SPO_GIFT_HEADER_ALIAS_MAP` (flat alias map built from nested alias dict)
4. Pre-built user/alias/solicitor lookups to avoid per-row DB queries
5. Per-row processing with `transaction.savepoint()` isolation:
   - Missionary resolved via `_match_missionary_name()` — None → skip + count in `unmatched_unresolved`
   - Contact: anonymous contact or `external_constituent_id` lookup — not found → skip + count in `contact_not_found`
   - Gift idempotency: skip if `external_gift_id` already exists
   - `Gift.objects.create()` with `external_gift_id`, `amount_cents`, `gift_date`, `donor_contact`
   - `GiftCredit.objects.get_or_create()` linking gift to missionary's Solicitor
   - `_maybe_create_prayer_intention()` if prayer_description non-empty
6. Summary JSON with per-missionary breakdown and all skip counts

### Task 2: import_spo_prayers() + TestIdempotency — TDD

**RED:** Added failing tests for `TestImportSpoPrayers` and `TestIdempotency`:
- `test_prayer_extracted_without_gift_creation` — PrayerIntention created, Gift.count()==0
- `test_prayer_dedup_separate_from_gift_import` — same file importable as both SPO_GIFT and SPO_PRAYER
- `test_reconcile_force_bypasses_dedup` — force=True on reconcile_missionaries
- `test_gift_import_force_bypasses_dedup` — force=True on import_spo_gifts

**GREEN:** Implemented `import_spo_prayers()`:
1. Same dedup/decode/parse pattern as import_spo_gifts but `ImportBatchType.SPO_PRAYER`
2. Skips rows with empty prayer_description (counted as skipped)
3. Best-effort: unresolvable missionary or contact → skip gracefully (prayer is not financial)
4. Links to existing Gift via `external_gift_id` if gift was previously imported; creates standalone prayer otherwise
5. `created_count` = prayer intentions created

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _maybe_create_prayer_intention() signature mismatch**
- **Found during:** Task 1 implementation
- **Issue:** Plan documented `_maybe_create_prayer_intention(description, contact, missionary)` but actual function in re_services.py is `(gift, prayer_text, contact, seen_prayers)` — requires Gift instance
- **Fix:** Called with actual signature `(gift, prayer_text, contact, seen_prayers)` passing the created Gift and a `seen_prayers` dict maintained per batch
- **Files modified:** apps/imports/spo_services.py

**2. [Rule 1 - Bug] Test solicitor name mismatches**
- **Found during:** Task 1 GREEN phase (3 tests failing)
- **Issue:** Test missionary users had first/last names in one order but CSV solicitor_name used reversed order, causing normalized name lookup to fail
- **Fix:** Corrected test data so CSV solicitor_name matches the User's actual full_name format
- **Files modified:** apps/imports/tests/test_spo_services.py

## Test Results

```
Ran 42 tests in 43.480s
OK
```

All `TestImportSpoGifts`, `TestImportSpoPrayers`, `TestIdempotency` plus all prior plan tests passing.

## Self-Check: PASSED
