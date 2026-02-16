---
phase: 14-core-analytics-endpoints
plan: 02
subsystem: api
tags: [django, drf, analytics, sorting, testing, pytest]

# Dependency graph
requires:
  - phase: 14-01
    provides: Query optimization and DRF serializers for analytics endpoints
  - phase: 13-02
    provides: Admin analytics endpoints with Subquery pattern
provides:
  - Zero-activity contacts show meaningful days_stalled (time since journal membership)
  - Stalled contacts endpoint supports sorting (days_stalled, full_name, owner_name, last_activity_date)
  - Safe query parameter handling with bounded defaults (limit, offset, sort_by, sort_dir)
  - Comprehensive test coverage for Phase 14 enhancements (conversion_rate, safe params, days_stalled, sorting)
affects: [17-cmon-admin-contacts-tab, 18-cmon-admin-analytics-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subquery annotation for correlated queries (journal_membership_date)"
    - "Expression-based sorting with Coalesce for null-safe ordering"
    - "Query parameter validation with fallback to safe defaults"
    - "Direction inversion for date-based sorting (older date = more stalled)"

key-files:
  created: []
  modified:
    - apps/insights/services.py
    - apps/insights/views.py
    - apps/insights/tests/test_views.py

key-decisions:
  - "Zero-activity contacts show days_stalled based on journal membership date (not null)"
  - "Invalid sort_by/sort_dir values fall back to defaults (not errors)"
  - "Direction inversion for date-based sorting: desc on days_stalled = asc on date"
  - "Comprehensive test coverage for all Phase 14 enhancements"

patterns-established:
  - "Subquery annotation pattern: journal_membership_date for zero-activity contacts"
  - "Safe parameter parsing: get_safe_int_param() with bounds, manual validation for enums"
  - "Expression-based sorting: SORT_FIELDS map with Coalesce for null handling"

# Metrics
duration: 4m 9s
completed: 2026-02-13
---

# Phase 14 Plan 02: Core Analytics Enhancements Summary

**Zero-activity contacts show meaningful stalled duration, stalled contacts sortable by 4 fields, and comprehensive test coverage for Phase 14 (conversion_rate, safe params, sorting)**

## Performance

- **Duration:** 4m 9s
- **Started:** 2026-02-13T21:40:01Z
- **Completed:** 2026-02-13T21:44:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Zero-activity contacts (in journals but no stage events) show integer days_stalled based on journal membership date
- Stalled contacts endpoint supports sorting by days_stalled, full_name, owner_name, last_activity_date
- 8 new tests covering conversion_rate, safe param handling, days_stalled fix, sorting, invalid params
- All tests pass (26 total in insights, 437 in full suite)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix days_stalled for zero-activity contacts and add sorting** - `adcec0b` (feat)
2. **Task 2: Add tests for all Phase 14 enhancements** - `54ae3b0` (test)

## Files Created/Modified
- `apps/insights/services.py` - Added journal_membership_date Subquery, days_stalled fix, sort_by/sort_dir parameters
- `apps/insights/views.py` - Added sort parameter parsing and validation to StalledContactsView
- `apps/insights/tests/test_views.py` - Added 8 new tests (18 original + 8 new = 26 total)

## Decisions Made

**1. Zero-activity contacts show days_stalled based on journal_membership_date**
- Rationale: Success criteria requires including zero-activity contacts with meaningful data. Time since journal membership shows how long they've been "neglected."
- Implementation: Added Subquery for earliest JournalContact.created_at, calculate days_stalled from membership date if no activity

**2. Invalid sort_by/sort_dir values fall back to defaults**
- Rationale: Safer UX than errors. Bad query params shouldn't break the endpoint.
- Implementation: Validate against whitelist, fall back to 'days_stalled' and 'desc' defaults

**3. Direction inversion for date-based sorting**
- Rationale: "Most stalled" means oldest date, so desc on days_stalled = asc on date
- Implementation: Invert effective_dir for days_stalled and last_activity_date sorts

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Journal model requires goal_amount (IntegrityError)**
- Problem: Test journal creation failed with NOT NULL constraint
- Resolution: Added goal_amount=Decimal('5000.00') to Journal.objects.create() in tests
- Files: apps/insights/tests/test_views.py (2 tests)

## Next Phase Readiness

**Ready for:**
- Phase 17 CMON-02: Stalled contacts tab can now sort by days_stalled/full_name/owner_name
- Frontend integration: Sorting parameters documented in OpenAPI schema

**Phase 14 Complete:**
- ✅ Query optimization (<20 queries per endpoint)
- ✅ DRF serializers for consistent response formatting
- ✅ Safe query parameter handling
- ✅ conversion_rate field in user performance
- ✅ Zero-activity contacts show days_stalled
- ✅ Stalled contacts sorting support
- ✅ Comprehensive test coverage

**No blockers.**

---
*Phase: 14-core-analytics-endpoints*
*Completed: 2026-02-13*
