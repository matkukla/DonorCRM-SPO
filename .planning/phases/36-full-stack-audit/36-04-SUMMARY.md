---
phase: 36-full-stack-audit
plan: 04
subsystem: api
tags: [dead-code, error-handling, drf, cleanup, permissions]

# Dependency graph
requires:
  - phase: 36-01
    provides: Research findings on dead code and inconsistencies
  - phase: 36-02
    provides: API parameter validation patterns (get_safe_int_param)
  - phase: 36-03
    provides: Performance audit completing prerequisite analysis
provides:
  - Dead code removed (PledgeFulfillmentError, frontend shims)
  - Unified DRF-convention error responses (detail key)
  - Access control matrix documentation in permissions.py
affects: [37-security-check]

# Tech tracking
tech-stack:
  added: []
  patterns: [DRF {'detail'} error response convention]

key-files:
  created: []
  modified:
    - apps/core/exceptions.py
    - apps/core/permissions.py
    - apps/insights/views.py
    - apps/insights/export_views.py
    - apps/insights/services.py
    - apps/imports/views.py

key-decisions:
  - "export_contacts_csv and export_gifts_csv in imports/services.py are NOT dead code -- still used by imports/views.py export endpoints"
  - "import_contacts_async Celery task is NOT dead -- still imported and used by ContactImportView"
  - "FundListSerializer left inline with comment (3 lines, not worth separate module)"
  - "MPDImportView error field in response payload left as-is (data field in rich response, not standalone error response)"

patterns-established:
  - "All API error responses use {'detail': '...'} format (DRF convention)"
  - "Access control matrix documented at top of core/permissions.py"

requirements-completed: [AUDIT-01]

# Metrics
duration: 6min
completed: 2026-02-24
---

# Phase 36 Plan 04: Code Quality Audit Summary

**Removed dead code (PledgeFulfillmentError, 4 frontend shims), unified 12 error responses to DRF {'detail'} convention, documented access control matrix**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-24T15:40:38Z
- **Completed:** 2026-02-24T15:47:05Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Removed PledgeFulfillmentError dead exception class (no importers found)
- Deleted 4 unused frontend re-export shim files (api/donations.ts, api/pledges.ts, hooks/useDonations.ts, hooks/usePledges.ts) -- zero imports anywhere
- Changed all 12 Response({'error': ...}) occurrences to Response({'detail': ...}) across insights views and export views
- Updated 7 test files to assert on 'detail' instead of 'error'
- Added access control matrix documentation to core/permissions.py
- Added documentation comments to FundListSerializer and ImportBatchListView

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove dead code and legacy shim files** - `09372db` (refactor)
2. **Task 2: Unify error response format and fix inconsistent patterns** - `9d675c1` (fix)

## Files Created/Modified
- `apps/core/exceptions.py` - Removed PledgeFulfillmentError dead exception
- `apps/core/permissions.py` - Added access control matrix documentation comment
- `apps/insights/views.py` - Changed 10 {'error'} to {'detail'} responses
- `apps/insights/export_views.py` - Changed 2 {'error'} to {'detail'} responses
- `apps/insights/services.py` - Changed get_user_drilldown to return 'detail' key
- `apps/imports/views.py` - Added documentation comments to FundListSerializer and ImportBatchListView
- `frontend/src/api/donations.ts` - Deleted (unused re-export shim)
- `frontend/src/api/pledges.ts` - Deleted (unused re-export shim)
- `frontend/src/hooks/useDonations.ts` - Deleted (unused re-export shim)
- `frontend/src/hooks/usePledges.ts` - Deleted (unused re-export shim)
- `apps/insights/tests/test_stage_contacts.py` - Updated error->detail assertion
- `apps/insights/tests/test_date_filtering.py` - Updated error->detail assertions
- `apps/insights/tests/test_user_drilldown.py` - Updated error->detail assertions
- `apps/insights/tests/test_user_detail.py` - Updated error->detail assertions
- `apps/insights/tests/test_csv_export.py` - Updated error->detail assertion

## Decisions Made
- Research claimed export_contacts_csv and export_gifts_csv were dead code superseded by new export_views.py -- investigation showed they are still actively used by imports/views.py ContactExportView and DonationExportView. Left in place.
- Research claimed import_contacts_async was dead Celery code -- investigation showed it is still imported and called by ContactImportView. Left in place.
- FundListSerializer is only 3 lines -- left inline with documentation comment rather than creating separate serializers.py module.
- MPDImportView includes `'error': upload.error_message` in a rich response body alongside other data fields -- this is a data field, not a standalone error response, so left as-is.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 5 additional test files asserting on 'error' key**
- **Found during:** Task 2 (Error response unification)
- **Issue:** Plan only identified 2 test files needing updates (test_stage_contacts.py, test_date_filtering.py), but 5 more test files also asserted on the 'error' key
- **Fix:** Updated all 7 test files: test_stage_contacts.py, test_date_filtering.py, test_user_drilldown.py, test_user_detail.py, test_csv_export.py
- **Files modified:** apps/insights/tests/ (5 additional test files)
- **Verification:** All 337 non-pre-existing tests pass
- **Committed in:** 9d675c1 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary correction -- changing error responses without updating all tests would have caused regressions.

## Issues Encountered
- 3 pre-existing test failures found (test_export_gifts_csv, test_counts_donations_by_week, test_returns_correct_stats) -- all related to amount_dollars returning integer instead of decimal string. Verified pre-existing via git stash test. Not in scope for this plan.
- `send_late_pledge_alert` in apps/core/email.py references removed Pledge model but is never imported/called. Out of scope per deviation rules (not in files_modified list). Logged as deferred item.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Codebase is cleaner: zero dead Donation/Pledge references in active code paths
- All API error responses now follow consistent DRF convention
- Access control matrix documented for future reference
- Ready for Phase 36 Plan 05 (remaining audit items)

---
*Phase: 36-full-stack-audit*
*Completed: 2026-02-24*
