---
phase: 51-data-scoping-admin-supervisor-default-to-own-data
plan: 01
subsystem: testing
tags: [permissions, pytest, factory-boy, role-based-access, tdd]

# Dependency graph
requires:
  - phase: 46-supervisor-coach-permissions
    provides: "get_visible_user_ids() function in apps/core/permissions.py"
provides:
  - "6 unit tests for get_visible_user_ids() covering all roles in correct RED/GREEN state"
  - "Test scaffold establishing TARGET behavior for Phase 51 implementation"
affects:
  - phase: 51-data-scoping-admin-supervisor-default-to-own-data plan 02 (implementation)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred import inside test body (from apps.core.permissions import ...) matching project style"
    - "Factory .build() for tests requiring no DB access (admin, missionary)"
    - "Assign supervised missionary explicitly to trigger current supervisor behavior in RED state"

key-files:
  created:
    - apps/core/tests/test_permissions.py
  modified: []

key-decisions:
  - "Supervisor test assigns a missionary (missionary.supervisors.add(sup)) to ensure current {own+supervised} behavior makes the test RED — a supervisor with no supervised users already returns {sup.id}, so the test would have passed incorrectly"

patterns-established:
  - "Wave 0 TDD: write target-behavior tests first, verify RED state before implementation, then implement in Plan 02"

requirements-completed:
  - SCOPE-01
  - SCOPE-02

# Metrics
duration: 17min
completed: 2026-03-14
---

# Phase 51 Plan 01: Data Scoping Test Scaffold Summary

**pytest scaffold with 6 role-behavior unit tests for get_visible_user_ids() in correct RED state: admin and supervisor fail asserting {own_id} while finance/read_only/coach/missionary pass**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-14T04:30:28Z
- **Completed:** 2026-03-14T04:47:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `apps/core/tests/test_permissions.py` with 6 deterministic unit tests for all roles
- Established correct RED state: 2 fail (admin, supervisor), 4 pass (finance, read_only, coach, missionary)
- Tests use deferred import pattern matching project style from `test_fiscal_year.py`
- DB-heavy tests use `@pytest.mark.django_db`; simple tests use `.build()` to avoid DB

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test_permissions.py scaffold (RED tests for admin + supervisor)** - `5d0e874` (test)

**Plan metadata:** (docs: complete plan — see final commit)

## Files Created/Modified
- `apps/core/tests/test_permissions.py` - 6 unit tests for get_visible_user_ids() covering all 6 roles

## Decisions Made
- Supervisor test assigns a missionary via `missionary.supervisors.add(sup)` to put the supervisor test in RED state. With no supervised missionaries, the current function already returns `{sup.id}` which would make the test pass incorrectly. Assigning a missionary means current code returns `{sup.id, missionary.id}`, causing the assertion `result == {sup.id}` to fail correctly.
- Admin test uses `.build()` (no DB hit) since after Plan 02 the admin branch returns `{user.id}` without any M2M queries. Factory's `.build()` auto-assigns a UUID so `admin.id` is non-None and the assertion is semantically correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Supervisor test initially passed (GREEN) instead of failing (RED)**
- **Found during:** Task 1 (initial test run)
- **Issue:** Plan specified supervisor test with no supervised users. Current code returns `{sup.id}` for a supervisor with zero supervised users, matching the target assertion `result == {sup.id}` — the test passed instead of being RED.
- **Fix:** Added `missionary.supervisors.add(sup)` to assign a missionary to the supervisor. Current code then returns `{sup.id, missionary.id}`, causing `result == {sup.id}` to fail correctly.
- **Files modified:** apps/core/tests/test_permissions.py
- **Verification:** Re-ran pytest — confirmed 2 FAILED (admin, supervisor), 4 PASSED
- **Committed in:** 5d0e874 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — incorrect RED state)
**Impact on plan:** Essential fix to ensure the test scaffold actually validates the target behavior change. No scope creep.

## Issues Encountered
- Initial supervisor test logic in plan description would have produced incorrect GREEN state — fixed by assigning a supervised missionary to trigger current behavior.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test scaffold complete and in correct RED state
- Plan 02 ready to implement: change `get_visible_user_ids()` so admin returns `{user.id}` and supervisor returns `{user.id}` (removing supervised_users M2M query from supervisor branch)
- All 6 tests will turn GREEN after Plan 02 implementation

---
*Phase: 51-data-scoping-admin-supervisor-default-to-own-data*
*Completed: 2026-03-14*
