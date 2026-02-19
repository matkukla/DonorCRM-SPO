---
phase: 21-dark-mode-ui-polish
plan: 02
subsystem: api, database, ui
tags: [django-signals, csv-export, formula-injection, react-query, cache-invalidation]

# Dependency graph
requires:
  - phase: 04-donations
    provides: "Donation model and signals infrastructure"
  - phase: 07-csv-import-export
    provides: "CSV export functions and FORMULA_PREFIXES constant"
  - phase: 14-admin-analytics
    provides: "StalledContactsCSVView and TeamActivityCSVView export endpoints"
provides:
  - "Donation edit signal that recalculates contact stats on both create and update"
  - "sanitize_csv_value() utility for CSV formula injection prevention"
  - "All 4 CSV export endpoints sanitized against spreadsheet formula injection"
  - "Frontend cache invalidation for contacts and dashboard on donation update"
affects: [csv-exports, donations, contact-stats]

# Tech tracking
tech-stack:
  added: []
  patterns: [owasp-csv-sanitization, signal-restructure-for-edit-support]

key-files:
  created: []
  modified:
    - apps/donations/signals.py
    - frontend/src/hooks/useDonations.ts
    - apps/imports/services.py
    - apps/insights/export_views.py

key-decisions:
  - "Used OWASP single-quote prefix for CSV sanitization (spreadsheet-native text-mode indicator)"
  - "Kept event creation, thank-you marking, and pledge fulfillment as create-only in signal"

patterns-established:
  - "sanitize_csv_value pattern: wrap user-entered string fields in all CSV export functions"
  - "Signal restructure pattern: stats update unconditional, side effects gated behind created flag"

# Metrics
duration: 4min
completed: 2026-02-17
---

# Phase 21 Plan 02: Donation Edit Stats Fix & CSV Export Sanitization Summary

**Fixed donation edit signal to recalculate contact stats on both create and update (QAL-11), and added OWASP CSV formula sanitization to all 4 export endpoints (QAL-12)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-17T16:40:13Z
- **Completed:** 2026-02-17T16:43:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Donation edits now trigger contact lifetime/monthly stats recalculation via restructured post_save signal
- Frontend useUpdateDonation hook invalidates contacts and dashboard queries for immediate UI refresh
- sanitize_csv_value() utility prevents spreadsheet formula injection using OWASP single-quote prefix
- All 4 CSV export endpoints (contacts, donations, stalled contacts, team activity) protected against formula injection

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix donation post_save signal to update stats on edits (QAL-11)** - `adaff1c` (fix)
2. **Task 2: Add CSV export formula sanitization to all 4 export endpoints (QAL-12)** - `c10086e` (feat)

## Files Created/Modified
- `apps/donations/signals.py` - Restructured post_save signal: update_giving_stats() runs on both create and edit, event/thank-you/pledge remain create-only
- `frontend/src/hooks/useDonations.ts` - Added contacts and dashboard query invalidation to useUpdateDonation onSuccess
- `apps/imports/services.py` - Added sanitize_csv_value() utility; applied to export_contacts_csv and export_donations_csv
- `apps/insights/export_views.py` - Imported sanitize_csv_value; applied to StalledContactsCSVView and TeamActivityCSVView

## Decisions Made
- Used OWASP single-quote prefix approach for CSV sanitization (spreadsheet applications interpret leading `'` as text-mode indicator and strip it from display)
- Kept event creation, thank-you marking, and pledge fulfillment gated behind `if created:` in the signal to prevent duplicate events/side effects on edits

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data integrity fixes complete: donation edits properly recalculate contact stats
- Security hardening complete: all CSV exports sanitized against formula injection
- Ready for Phase 21 Plan 03

## Self-Check: PASSED

All files exist. All commits verified (adaff1c, c10086e).

---
*Phase: 21-dark-mode-ui-polish*
*Completed: 2026-02-17*
