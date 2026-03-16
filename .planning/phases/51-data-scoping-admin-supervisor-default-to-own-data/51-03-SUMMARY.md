---
phase: 51-data-scoping-admin-supervisor-default-to-own-data
plan: "03"
subsystem: api
tags: [django, permissions, dashboard, role-based-access]

# Dependency graph
requires:
  - phase: 51-data-scoping-admin-supervisor-default-to-own-data
    provides: "get_visible_user_ids() returning {user.id} for admin/supervisor (Phase 51 core)"
provides:
  - "_resolve_target_user() with role-based short-circuit granting admin/supervisor explicit ?user_id= selection rights"
  - "TestResolveTargetUser tests confirming supervisor and admin can use ?user_id= without 403"
affects:
  - phase-52-view-as-backend
  - phase-53-view-as-frontend

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two distinct access patterns: get_visible_user_ids() governs default list-view scoping; _resolve_target_user() governs explicit dashboard dropdown selection — handled separately"

key-files:
  created: []
  modified:
    - apps/dashboard/views.py
    - apps/dashboard/tests/test_views.py

key-decisions:
  - "Role guard in _resolve_target_user() placed BEFORE get_visible_user_ids() call — admin and supervisor bypass visibility check entirely for dashboard dropdown, not after checking it"
  - "get_visible_user_ids() in apps/core/permissions.py left completely untouched — Phase 51 default scoping change is intact"

patterns-established:
  - "Dashboard dropdown selection (explicit ?user_id=) vs default data scoping are independent access patterns: the former is gated by role check, the latter by get_visible_user_ids()"

requirements-completed:
  - SCOPE-01
  - SCOPE-02

# Metrics
duration: 2min
completed: "2026-03-16"
---

# Phase 51 Plan 03: _resolve_target_user() Regression Fix Summary

**Role guard added to _resolve_target_user() so admin/supervisor can select any missionary via dashboard dropdown without 403, while get_visible_user_ids() default scoping remains intact**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T13:54:38Z
- **Completed:** 2026-03-16T13:56:37Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed Phase 51 regression where supervisor/admin received 403 when selecting a missionary from the dashboard dropdown via ?user_id=
- Added role-based short-circuit in _resolve_target_user() before get_visible_user_ids() call — admin and supervisor bypass visibility check for explicit selection
- Added TestResolveTargetUser with 4 tests confirming supervisor can select missionary (200), admin can select missionary (200), missionary cross-user blocked (403), and nonexistent user_id returns 404
- All 42 dashboard tests pass; all 6 core permissions tests (Phase 51 scoping) pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix _resolve_target_user() to allow admin/supervisor dashboard selection** - `1ce8de5` (fix)
2. **Task 2: Add tests verifying supervisor and admin can use ?user_id= without 403** - `01b7f53` (test)

**Plan metadata:** _see final docs commit_

## Files Created/Modified
- `apps/dashboard/views.py` - Added role guard in _resolve_target_user(); updated docstring to document two distinct access patterns
- `apps/dashboard/tests/test_views.py` - Added TestResolveTargetUser class with 4 tests; updated import to include AdminUserFactory, SupervisorUserFactory

## Decisions Made
- Role guard placed BEFORE get_visible_user_ids() call — not after — so admin/supervisor entirely bypass the visibility check, not just get a different result from it
- get_visible_user_ids() in apps/core/permissions.py is NOT modified, preserving the Phase 51 default data scoping change

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 51 is now complete — admin/supervisor default to own data (Phase 51 core) and can select any missionary via dashboard dropdown (this plan)
- Phase 52 (View As backend: middleware, permissions, mutation blocking) is ready to begin
- The foundation of role-based scoping is solid: get_visible_user_ids() governs list views, _resolve_target_user() governs dashboard selection

## Self-Check: PASSED

- FOUND: apps/dashboard/views.py
- FOUND: apps/dashboard/tests/test_views.py
- FOUND: 51-03-SUMMARY.md
- FOUND commit: 1ce8de5 (fix - _resolve_target_user role guard)
- FOUND commit: 01b7f53 (test - TestResolveTargetUser 4 tests)
- All 42 dashboard tests GREEN
- All 6 core permissions tests GREEN

---
*Phase: 51-data-scoping-admin-supervisor-default-to-own-data*
*Completed: 2026-03-16*
