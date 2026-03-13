---
phase: 49-goal-page-data-model-backend
plan: "02"
subsystem: api
tags: [django, fiscal-year, gift-aggregation, refactor, python]

# Dependency graph
requires:
  - phase: 49-01
    provides: failing test stubs for fiscal_year.py functions and UserFactory goal fields

provides:
  - apps/core/fiscal_year.py with fiscal_year_start(), fiscal_year_end(), months_remaining()
  - apps/core/gift_utils.py with FREQUENCY_MULTIPLIERS and _monthly_equivalent_aggregate()
  - apps/dashboard/services.py updated to import from apps.core.gift_utils

affects: [49-03, 49-04, goal-service, goal-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fiscal year July 1 - June 30 expressed as pure Python date arithmetic (no Django dependency)"
    - "Shared SQL aggregation helpers live in apps/core/ for use across multiple app services"
    - "months_remaining() uses minimum guard of 1 to prevent division-by-zero in goal calculations"

key-files:
  created:
    - apps/core/fiscal_year.py
    - apps/core/gift_utils.py
  modified:
    - apps/dashboard/services.py

key-decisions:
  - "FREQUENCY_MULTIPLIERS and _monthly_equivalent_aggregate extracted to apps/core/gift_utils.py so goal_services.py can import them without circular dependency on dashboard app"
  - "Case and When removed from dashboard/services.py imports after extraction — verified no remaining usages"
  - "RecurringGiftFrequency removed from dashboard/services.py imports after extraction — was only used inside FREQUENCY_MULTIPLIERS dict"
  - "Pre-existing test failures (20 stubs blocked on Plan 03 User model migration) documented as out-of-scope; zero new failures introduced by this plan"

patterns-established:
  - "fiscal_year.py: pure Python with FISCAL_YEAR_START_MONTH = 7 constant"
  - "gift_utils.py: Django ORM helpers in apps/core/ shared across apps"

requirements-completed: [FISC-01, FISC-02]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 49 Plan 02: Shared Fiscal Year and Gift Aggregation Utilities Summary

**Pure-Python fiscal year utility (fiscal_year_start/end/months_remaining) and extracted SQL gift aggregation helper (_monthly_equivalent_aggregate) in apps/core/, unblocking Plan 03 migrations and Plan 04 goal service.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-13T03:11:31Z
- **Completed:** 2026-03-13T03:15:18Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 updated)

## Accomplishments
- Created `apps/core/fiscal_year.py` — pure Python July-1/June-30 fiscal year logic; all 8 TDD tests pass GREEN
- Created `apps/core/gift_utils.py` — FREQUENCY_MULTIPLIERS dict and _monthly_equivalent_aggregate() SQL helper extracted from dashboard services
- Updated `apps/dashboard/services.py` — removed local definitions, added import from apps.core.gift_utils; zero new test failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Create apps/core/fiscal_year.py** - `e8f7e5f` (feat)
2. **Task 2: Extract gift_utils and update dashboard import** - `92c7036` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `apps/core/fiscal_year.py` - fiscal_year_start(), fiscal_year_end(), months_remaining() pure functions
- `apps/core/gift_utils.py` - FREQUENCY_MULTIPLIERS dict and _monthly_equivalent_aggregate() SQL aggregation helper
- `apps/dashboard/services.py` - Updated imports: removed local FREQUENCY_MULTIPLIERS/_monthly_equivalent_aggregate, added import from apps.core.gift_utils

## Decisions Made
- Extracted gift aggregation to `apps/core/` rather than keeping in `apps/dashboard/` — goal service (Plan 04) needs the same aggregation and importing from dashboard would create a cross-app dependency in the wrong direction
- `Case` and `When` removed from dashboard services.py imports after confirming they were only used inside the extracted function
- `RecurringGiftFrequency` removed from dashboard services.py imports after confirming it was only used inside the extracted `FREQUENCY_MULTIPLIERS` dict

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- 20 pre-existing test failures in `apps/dashboard/tests/` — all stub tests from Plan 01 that depend on new User model fields (`monthly_support_goal_cents`, `goal_weeks`) not yet added by Plan 03 migrations. Confirmed these failures existed before this plan's changes by stashing and re-running. Zero new failures introduced.

## Next Phase Readiness
- Plan 03 (migration + model changes) can proceed — `fiscal_year_start()` and `months_remaining()` are importable
- Plan 04 (goal service) can import `_monthly_equivalent_aggregate` from `apps.core.gift_utils`
- No blockers for subsequent plans in phase 49

## Self-Check: PASSED

- apps/core/fiscal_year.py: FOUND
- apps/core/gift_utils.py: FOUND
- 49-02-SUMMARY.md: FOUND
- Commit e8f7e5f (fiscal_year.py): FOUND
- Commit 92c7036 (gift_utils.py + services.py): FOUND

---
*Phase: 49-goal-page-data-model-backend*
*Completed: 2026-03-13*
