---
phase: 47-fix-coach-role-gaps
plan: 01
subsystem: testing
tags: [pytest, fixtures, role-vocabulary, missionary, UserRole]

# Dependency graph
requires:
  - phase: 43-roles-redesign
    provides: "renamed staff->missionary in UserRole choices and migration 0005"
provides:
  - "Test fixtures aligned with current UserRole vocabulary (role='missionary')"
  - "conftest.py authenticated_client uses correct role"
  - "SPO import tests use correct role"
  - "Insights drilldown role assertion corrected"
affects: [47-fix-coach-role-gaps, test-suite-health]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - conftest.py
    - apps/imports/tests/test_spo_views.py
    - apps/imports/tests/test_spo_csv_fixture_mapping.py
    - apps/insights/tests/test_user_drilldown.py

key-decisions:
  - "Pre-existing test failures (test_export_gifts_csv, TestActivityHeatmap, test_counts_donations_by_week) confirmed out-of-scope — not caused by role changes"
  - "total_donations assertion corrected from 15000.0 (raw cents) to 150.0 (dollars) — stale comment said 'cents' but API returns dollars"

patterns-established: []

requirements-completed: [ROLE-01]

# Metrics
duration: 5min
completed: 2026-03-10
---

# Phase 47 Plan 01: Fix Stale Role Strings in Test Fixtures Summary

**Four stale role='staff' fixture strings and one wrong role assertion replaced with role='missionary' to align test suite with Phase 43 UserRole vocabulary rename.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-10T14:21:00Z
- **Completed:** 2026-03-10T14:26:00Z
- **Tasks:** 2 (1 committed, 1 verified only)
- **Files modified:** 4

## Accomplishments
- Replaced `role='staff'` with `role='missionary'` in all four target files
- Fixed stale `assertEqual(role, 'staff')` assertion in test_user_drilldown.py
- Confirmed zero regressions in contacts, users, imports, insights test suites
- Pre-existing failures (9 total) confirmed pre-existing via git stash verification

## Task Commits

1. **Task 1: Replace stale role='staff' strings and fix role assertion** - `b8b95cf` (fix)
2. **Task 2: Broader test suite regression check** - No commit (verification only, no file changes)

## Files Created/Modified
- `conftest.py` - authenticated_client fixture: role='staff' -> role='missionary'
- `apps/imports/tests/test_spo_views.py` - _make_staff() helper: role='staff' -> role='missionary'
- `apps/imports/tests/test_spo_csv_fixture_mapping.py` - _make_staff_owner() helper: role='staff' -> role='missionary'
- `apps/insights/tests/test_user_drilldown.py` - role assertEqual: 'staff' -> 'missionary'; also fixed total_donations: 15000.0 -> 150.0

## Decisions Made
- Pre-existing test failures (test_export_gifts_csv, 7x TestActivityHeatmap, test_counts_donations_by_week) are out-of-scope — confirmed pre-existing via git stash
- total_donations assertion bug auto-fixed under Rule 1: expected raw cents (15000) but API returns dollars (150.0); stale comment was misleading

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale total_donations assertion in test_user_drilldown.py**
- **Found during:** Task 1 (verifying role assertion change)
- **Issue:** `assertEqual(total_donations, 15000.0)` expected raw cent value but API returns dollar amount (150.0). Gifts are 10000 + 5000 cents = $150.00.
- **Fix:** Changed expected value from 15000.0 to 150.0 and updated comment
- **Files modified:** apps/insights/tests/test_user_drilldown.py
- **Verification:** All 24 targeted tests pass after fix
- **Committed in:** b8b95cf (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug — wrong expected value in test assertion)
**Impact on plan:** Auto-fix necessary for correctness; test was asserting wrong value. No scope creep.

## Issues Encountered
- pytest-cov raises INTERNALERROR due to permission denied on htmlcov/. Resolved by running with --no-cov. Pre-existing infrastructure issue, not caused by this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test fixtures now use correct role vocabulary; plan 47-02 can proceed without IntegrityError from stale 'staff' role
- 9 pre-existing test failures remain in insights (heatmap, team trends) and imports (gift CSV export) — deferred

---
*Phase: 47-fix-coach-role-gaps*
*Completed: 2026-03-10*
