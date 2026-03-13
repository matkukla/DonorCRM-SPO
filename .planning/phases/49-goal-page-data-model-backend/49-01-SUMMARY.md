---
phase: 49-goal-page-data-model-backend
plan: 01
subsystem: testing
tags: [pytest, tdd, fiscal-year, goals, django, wave-0]

# Dependency graph
requires: []
provides:
  - "8 failing test stubs for fiscal_year utility (FISC-01, FISC-02 boundary cases)"
  - "4 failing test stubs for get_goal_progress service (GOAL-04)"
  - "5 failing integration test stubs for /api/v1/goals/me/ endpoint (GOAL-02, GOAL-03)"
  - "UserFactory updated with monthly_support_goal_cents and goal_weeks fields"
affects:
  - "49-02 (fiscal year implementation — must make 8 fiscal tests pass)"
  - "49-03 (data model migration — must rename monthly_goal; factory already updated)"
  - "49-04 (goal API implementation — must make 9 goal service + views tests pass)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 TDD: test stubs use deferred inline imports so all 17 items collect cleanly before implementations exist"

key-files:
  created:
    - apps/core/tests/test_fiscal_year.py
    - apps/users/tests/test_goal_services.py
    - apps/users/tests/test_views_goals.py
  modified:
    - apps/users/tests/factories.py

key-decisions:
  - "Deferred imports (inside test bodies) rather than module-level imports — allows pytest to collect all 17 test items even when implementation modules don't yet exist"
  - "monthly_support_goal_cents uses integer cents (random_int 100000-1000000); goal_weeks defaults to 52 in UserFactory"
  - "months_remaining uses closed-interval minimum 1: June 30 returns 1, not 0"
  - "months_remaining interpretation: Aug 15 returns 10 (counts months AFTER the current month through June)"

patterns-established:
  - "Wave 0 test stubs: deferred imports enable clean collection — import happens inside each test function, fails at runtime not at collection time"

requirements-completed: [FISC-01, FISC-02, GOAL-02, GOAL-03, GOAL-04]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 49 Plan 01: Wave 0 Test Scaffolds Summary

**17 failing pytest stubs across 3 test files covering fiscal year utilities, goal progress service, and goals API endpoint — all fail for the right reason (missing modules/endpoints)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-13T03:06:06Z
- **Completed:** 2026-03-13T03:09:30Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created apps/core/tests/test_fiscal_year.py with 8 stubs covering all FISC-01 and FISC-02 boundary cases (July 1 exact, June 30 rollover, June minimum guard)
- Created apps/users/tests/test_goal_services.py with 4 stubs for GOAL-04 effective_monthly_support calculation including scoping test
- Created apps/users/tests/test_views_goals.py with 5 stubs for GOAL-02/GOAL-03 covering PATCH goal, PATCH journals, replace-all semantics, GET field presence, and auth guard
- Updated UserFactory to replace Decimal monthly_goal with integer monthly_support_goal_cents and add goal_weeks = 52

## Task Commits

Each task was committed atomically:

1. **Task 1: Create apps/core/tests/ package and test_fiscal_year.py stubs** - `85b7f93` (test)
2. **Task 2: Create test_goal_services.py and test_views_goals.py stubs** - `f3bb617` (test)
3. **Task 3: Update UserFactory to use monthly_support_goal_cents** - `0a780fe` (chore)
4. **Deviation fix: Defer imports for collectability** - `d3e15b0` (test)

## Files Created/Modified
- `apps/core/tests/test_fiscal_year.py` - 8 test functions for fiscal_year_start, fiscal_year_end, months_remaining
- `apps/users/tests/test_goal_services.py` - 4 test functions for get_goal_progress service
- `apps/users/tests/test_views_goals.py` - 5 integration test functions for /api/v1/goals/me/ endpoint
- `apps/users/tests/factories.py` - Renamed monthly_goal to monthly_support_goal_cents (int cents), added goal_weeks = 52

## Decisions Made
- Used deferred imports (inline inside test body) instead of module-level imports so all 17 items collect cleanly before implementation modules exist — avoids ImportError at collection time
- months_remaining returns 10 for Aug 15 (counts months AFTER the current month: Sep through Jun = 10)
- months_remaining minimum guard returns 1 even on June 30 (not 0)
- UserFactory monthly_support_goal_cents range: 100,000–1,000,000 integer cents

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restructured test imports from module-level to inline for collectability**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** Module-level `from apps.core.fiscal_year import ...` caused ImportError at collection time, preventing pytest from discovering all 17 items; the overall plan verification expected "17 test items collected, 0 errors"
- **Fix:** Moved all imports inside each test function body — tests still fail with ModuleNotFoundError at runtime (correct RED state) but now all 17 collect cleanly
- **Files modified:** apps/core/tests/test_fiscal_year.py, apps/users/tests/test_goal_services.py
- **Verification:** `pytest --collect-only` shows `17 tests collected in 0.44s`
- **Committed in:** d3e15b0

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test structure)
**Impact on plan:** Essential fix — plan specified both "fail with ModuleNotFoundError" and "17 items collected, 0 errors." Deferred imports satisfy both requirements simultaneously.

## Issues Encountered
None beyond the import structure fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 17 Wave 0 test stubs are in place and correctly failing
- Plan 02 can implement apps/core/fiscal_year.py — 8 fiscal tests will turn GREEN
- Plan 03 can run the data model migration — UserFactory already updated for new field names
- Plan 04 can implement goal_services.py and the /api/v1/goals/me/ endpoint — 9 remaining tests will turn GREEN

---
*Phase: 49-goal-page-data-model-backend*
*Completed: 2026-03-13*
