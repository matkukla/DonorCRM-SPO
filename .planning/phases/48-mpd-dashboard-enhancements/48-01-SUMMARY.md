---
phase: 48-mpd-dashboard-enhancements
plan: 01
subsystem: api
tags: [django, rest-framework, mpd, decimal-field, tdd]

# Dependency graph
requires:
  - phase: 47
    provides: MPDSnapshot model with monthly_average DecimalField already in database
provides:
  - monthly_average field exposed in /api/v1/imports/mpd/me/ response
  - monthly_average field exposed in /api/v1/imports/mpd/overview/ per-missionary entries
  - automated tests for both MPD view endpoints (MPD-01, MPD-02 coverage)
affects: [48-02, frontend MPD dashboard monthly average tile, admin MPD overview table]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DecimalField to string serialization: str(field) if field is not None else None"
    - "TDD: write failing tests first, then minimal implementation to pass"

key-files:
  created:
    - apps/imports/tests/test_mpd_views.py
  modified:
    - apps/imports/views.py

key-decisions:
  - "monthly_average positioned after user_name and before current_mpd_cap in MPDOverviewView dict (matches intended table column order: Missionary | Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining)"
  - "Pre-existing test_export_gifts_csv failure is out of scope — confirmed pre-existing before this plan's changes, logged to deferred items"

patterns-established:
  - "MPD view serialization pattern: DecimalField read as snapshot.field, serialized with str() or None"

requirements-completed: [MPD-01, MPD-02]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 48 Plan 01: MPD Monthly Average API Fields Summary

**Exposed MPDSnapshot.monthly_average through /mpd/me/ and /mpd/overview/ endpoints with 4 TDD-driven tests confirming correct string serialization and null handling**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-12T16:13:26Z
- **Completed:** 2026-03-12T16:14:45Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `MPDMyDataView.get()` now returns `monthly_average` (string decimal or null) in its response dict
- `MPDOverviewView.get()` now returns `monthly_average` in each per-missionary dict entry, positioned before `current_mpd_cap`
- 4 automated tests cover both views: presence of value, null handling, overview content, and admin-only 403 enforcement

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for monthly_average in both MPD views** - `5f946bc` (test)
2. **Task 2: Add monthly_average to MPDMyDataView and MPDOverviewView** - `62a006d` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD tasks have two commits: test (RED) then feat (GREEN)_

## Files Created/Modified

- `apps/imports/tests/test_mpd_views.py` — 4 tests covering monthly_average in /mpd/me/ and /mpd/overview/ (created)
- `apps/imports/views.py` — Added monthly_average line to both view response dicts (modified)

## Decisions Made

- `monthly_average` positioned after `user_name` and before `current_mpd_cap` in MPDOverviewView to match intended column order: Missionary | Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining
- Pre-existing `test_export_gifts_csv` failure confirmed out of scope (failed identically before this plan's changes)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing `test_export_gifts_csv` failure in `apps/imports/tests/test_services.py` was present before this plan's changes. Out of scope per deviation rules — logged to deferred items.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend MPD fields complete for plan 48-01
- Plan 48-02 (frontend) can now read `monthly_average` from both API endpoints
- No blockers

## Self-Check: PASSED

- FOUND: apps/imports/tests/test_mpd_views.py
- FOUND: apps/imports/views.py (modified)
- FOUND: .planning/phases/48-mpd-dashboard-enhancements/48-01-SUMMARY.md
- FOUND: commit 5f946bc (test RED phase)
- FOUND: commit 62a006d (feat GREEN phase)

---
*Phase: 48-mpd-dashboard-enhancements*
*Completed: 2026-03-12*
