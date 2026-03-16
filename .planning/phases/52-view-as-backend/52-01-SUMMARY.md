---
phase: 52-view-as-backend
plan: 01
subsystem: testing
tags: [pytest, django, rest_framework, tdd, view-as, middleware, permissions]

# Dependency graph
requires:
  - phase: 51-data-scoping
    provides: "get_visible_user_ids() function in apps/core/permissions.py"
provides:
  - "RED test scaffold for ViewAsMiddleware (12 tests, VIEWAS-07 + VIEWAS-08)"
  - "RED test scaffold for ViewableUsersView (7 tests, VIEWAS-12)"
  - "RED test for get_visible_user_ids view_as scoping override (1 test, Phase 52 signature change)"
affects: [52-02-middleware, 52-03-permissions-update, 52-04-viewable-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred import pattern: factories imported inline inside test bodies to allow collection before implementation modules exist"
    - "RED test scaffolding before any implementation: all 20 new tests fail in RED state"

key-files:
  created:
    - apps/core/tests/test_middleware.py
    - apps/users/tests/test_views_viewable.py
  modified:
    - apps/core/tests/test_permissions.py

key-decisions:
  - "test_get_allowed_in_view_as and test_admin_can_view_as_any_missionary assert status_code != 403 (not == 200) — middleware may pass through to a view that returns other codes"
  - "test_supervisor_allowed_for_assigned uses missionaries.supervisors.add() M2M relationship consistent with Phase 51 patterns"
  - "test_view_as_overrides_scoping uses .build() (no DB) for both admin and view_as_user since get_visible_user_ids is synchronous and doesn't query those user objects"

patterns-established:
  - "Deferred import inside test body: prevents import errors before implementation modules exist — established Phase 49, continued here"
  - "RED scaffold precedes all implementation plans in Phase 52 (Nyquist compliance)"

requirements-completed: [VIEWAS-07, VIEWAS-08, VIEWAS-12]

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 52 Plan 01: View As Backend Test Scaffolds Summary

**20 pytest-django RED tests covering ViewAsMiddleware mutation blocking, permission validation, ViewableUsersView endpoint, and get_visible_user_ids view_as scoping override**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T15:04:43Z
- **Completed:** 2026-03-16T15:07:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 12 failing tests in test_middleware.py for VIEWAS-07 (mutation blocking) and VIEWAS-08 (permission validation) — awaiting Plan 02 implementation
- 7 failing tests in test_views_viewable.py for VIEWAS-12 (viewable users endpoint) — awaiting Plan 04 implementation
- 1 failing test appended to test_permissions.py for view_as scoping override (TypeError on wrong signature) — awaiting Plan 03 implementation
- Zero regressions: all 6 pre-existing test_permissions.py tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for ViewAsMiddleware** - `5468389` (test)
2. **Task 2: Write failing tests for ViewableUsersView and view_as scoping override** - `4dc113b` (test)

**Plan metadata:** (docs commit follows)

_Note: TDD plan — all tasks produce RED test commits; no GREEN commits in this plan_

## Files Created/Modified
- `apps/core/tests/test_middleware.py` — 12 RED tests for ViewAsMiddleware (VIEWAS-07, VIEWAS-08)
- `apps/users/tests/test_views_viewable.py` — 7 RED tests for ViewableUsersView (VIEWAS-12)
- `apps/core/tests/test_permissions.py` — appended test_view_as_overrides_scoping (Phase 52 signature change)

## Decisions Made
- `test_get_allowed_in_view_as` and `test_admin_can_view_as_any_missionary` assert `status_code != 403` rather than `== 200` — the middleware's job is to NOT block these; the underlying view may return any code
- `test_supervisor_allowed_for_assigned` uses `missionaries.supervisors.add()` consistent with Phase 51 M2M relationship pattern
- `test_view_as_overrides_scoping` uses `.build()` for both users — function is synchronous and doesn't query the user objects directly, so no DB needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Coverage plugin raised PermissionError on htmlcov directory — worked around with `--no-cov` flag for verification runs. Not a code issue; pre-existing environment permissions problem.

## Next Phase Readiness
- All RED tests ready; Plans 02-04 can implement middleware, permissions update, and viewable endpoint against these test contracts
- Plan 02 (middleware) owns 12 tests in test_middleware.py
- Plan 03 (permissions update) owns test_view_as_overrides_scoping in test_permissions.py
- Plan 04 (viewable endpoint) owns 7 tests in test_views_viewable.py

---
*Phase: 52-view-as-backend*
*Completed: 2026-03-16*
