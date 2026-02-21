---
phase: 29-re-import-gifts-recurring
plan: 01
subsystem: api
tags: [csv-import, raisers-edge, gift, gift-credit, prayer-intention, multi-row-grouping, m2m-migration]

# Dependency graph
requires:
  - phase: 28-re-import-pipeline-constituents-solicitors
    provides: "Shared RE import utilities: decode_csv_bytes, check_duplicate_import, _build_header_mapping, normalize_solicitor_name"
  - phase: 27-foundation-models
    provides: "Gift, GiftCredit, PrayerIntention models, ImportBatch with RE_GIFT type, Contact.external_constituent_id"
provides:
  - "PrayerIntention.gifts M2M field (replaces FK to Gift)"
  - "import_re_gifts() orchestrator with multi-row grouping, savepoint isolation, prayer auto-creation"
  - "Gift import helpers: _parse_amount_to_cents, _parse_date, _build_fund_lookup, _build_solicitor_lookup, _group_rows_by_id"
  - "Prayer auto-creation: _maybe_create_prayer_intention with PRAYER_STOPLIST and dedup by contact + text"
  - "GIFT_HEADER_ALIASES (36 aliases) and GIFT_REQUIRED_CANONICAL"
  - "Management command: import_re_gifts with --owner flag"
  - "API endpoint: POST /api/v1/imports/re/gifts/"
affects: [29-02, phase-32]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-pass multi-row grouping: first pass groups by ID, second pass creates records"
    - "Savepoint-per-group error isolation: one group failure doesn't roll back entire import"
    - "Prayer auto-creation inline during gift import with stoplist + case-insensitive dedup"
    - "Amount parsing from dollar strings to cents via Decimal for precision"

key-files:
  created:
    - apps/prayers/migrations/0002_remove_prayerintention_gift_prayerintention_gifts.py
    - apps/imports/management/commands/import_re_gifts.py
  modified:
    - apps/prayers/models.py
    - apps/prayers/admin.py
    - apps/imports/re_services.py
    - apps/imports/views.py
    - apps/imports/urls.py

key-decisions:
  - "Gift amount sourced from dedicated amount column on first row, NOT summed from credits"
  - "Missing contacts skip entire gift group (per locked CONTEXT.md decision)"
  - "Unknown solicitors skip credit only, logged as unmatched (not auto-created)"
  - "Prayer dedup by (contact.id, normalized_text_lowercase) with database fallback via __iexact"
  - "Prayer title truncated at last word boundary before 80 chars for clean display"
  - "Credit amount defaults to gift amount when credit_amount column is empty or zero"

patterns-established:
  - "Two-pass grouping pattern: _group_rows_by_id() reusable for RecurringGift import"
  - "Savepoint-per-group pattern for error-isolated batch processing"
  - "Prayer auto-creation with stoplist and M2M dedup pattern"

requirements-completed: [IMP-03, IMP-10]

# Metrics
duration: 4min
completed: 2026-02-20
---

# Phase 29 Plan 01: RE Gift Import Summary

**Multi-row gift grouping with solicitor credit splitting, PrayerIntention M2M migration, and prayer auto-creation from RE CSV descriptions via stoplist-filtered dedup**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T02:54:05Z
- **Completed:** 2026-02-21T02:58:26Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Migrated PrayerIntention.gift FK to PrayerIntention.gifts M2M field, enabling multiple gifts per prayer
- Built import_re_gifts() orchestrator with two-pass grouping by Gift ID, savepoint-per-group isolation, Contact lookup, fund matching, GiftCredit creation per solicitor row, and inline prayer auto-creation
- Added 6 shared helper functions (_parse_amount_to_cents, _parse_date, _build_fund_lookup, _build_solicitor_lookup, _group_rows_by_id, _maybe_create_prayer_intention) plus PRAYER_STOPLIST and GIFT_HEADER_ALIASES
- Created management command (import_re_gifts --owner) and API endpoint (POST /api/v1/imports/re/gifts/) both sharing the same service layer

## Task Commits

Each task was committed atomically:

1. **Task 1: PrayerIntention M2M migration and RE Gift import service with prayer auto-creation** - `c234124` (feat)
2. **Task 2: RE Gift management command and API endpoint** - `6c8d3df` (feat)

## Files Created/Modified
- `apps/prayers/models.py` - Changed PrayerIntention.gift FK to PrayerIntention.gifts M2M
- `apps/prayers/admin.py` - Removed gift from list_display (M2M incompatible)
- `apps/prayers/migrations/0002_remove_prayerintention_gift_prayerintention_gifts.py` - FK-to-M2M migration
- `apps/imports/re_services.py` - Added gift import helpers, GIFT_HEADER_ALIASES, and import_re_gifts() orchestrator
- `apps/imports/management/commands/import_re_gifts.py` - CLI command for gift CSV import with prayer/solicitor summary
- `apps/imports/views.py` - Added REGiftImportView API endpoint
- `apps/imports/urls.py` - Added re/gifts/ URL pattern

## Decisions Made
- Gift amount sourced from dedicated amount column on first row of each group, NOT summed from solicitor credits
- Missing contacts (constituent_id not found in DonorCRM) skip the entire gift group, per locked CONTEXT.md decision
- Unknown solicitors cause credit to be skipped (not auto-created), with names collected in unmatched_solicitors summary for admin review
- Prayer dedup uses (contact.id, normalized_text_lowercase) as in-memory key with database fallback via description__iexact query
- Prayer title truncated at last word boundary before 80 characters for clean display
- When credit_amount column is empty or zero, credit defaults to the full gift amount_cents
- PRAYER_STOPLIST contains 20 conservative entries (n/a, na, none, test, general, same as above, etc.)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Gift import helpers (_parse_amount_to_cents, _parse_date, _build_fund_lookup, _build_solicitor_lookup, _group_rows_by_id) ready for reuse in Plan 02's RecurringGift importer
- Two-pass grouping pattern established for RecurringGift import
- PRAYER_STOPLIST and _maybe_create_prayer_intention available if recurring gifts need prayer support

## Self-Check: PASSED

All 7 files verified present. Both task commits (c234124, 6c8d3df) verified in git log.

---
*Phase: 29-re-import-gifts-recurring*
*Completed: 2026-02-20*
