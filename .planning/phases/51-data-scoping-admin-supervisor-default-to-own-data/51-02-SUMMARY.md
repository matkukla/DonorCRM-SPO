---
phase: 51-data-scoping-admin-supervisor-default-to-own-data
plan: 02
subsystem: api
tags: [permissions, role-based-access, get_visible_user_ids, data-scoping, pytest]

# Dependency graph
requires:
  - phase: 51-data-scoping-admin-supervisor-default-to-own-data plan 01
    provides: "6 RED unit tests for get_visible_user_ids() covering all roles"
  - phase: 46-supervisor-coach-permissions
    provides: "get_visible_user_ids() function and supervised_users M2M in apps/core/permissions.py"
provides:
  - "Updated get_visible_user_ids() returning {user.id} for admin and supervisor roles"
  - "Admin and supervisor default to own data — no all-access by default"
  - "Finance and read_only remain as only all-access roles (return None sentinel)"
  - "All 6 test_permissions.py tests GREEN"
  - "test_m2m_assignments.py updated to assert Phase 51 supervisor behavior"
affects:
  - phase: 52-view-as-backend (middleware will re-enable cross-user access for admin/supervisor)
  - "All 13 caller views automatically scoped — no per-view changes needed"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sentinel pattern: None return means all-access; set return means scoped — finance/read_only are now the only None-returning roles"
    - "Fallthrough pattern: admin/supervisor/missionary all hit return {user.id} without explicit branches"

key-files:
  created: []
  modified:
    - apps/core/permissions.py
    - apps/users/tests/test_m2m_assignments.py

key-decisions:
  - "Admin and supervisor branches removed from get_visible_user_ids(); fallthrough return {user.id} handles all non-coach non-finance roles uniformly"
  - "15 pre-existing test failures confirmed not caused by Phase 51 changes (were failing before commit f287e7f); documented in deferred-items.md, out of scope"
  - "dashboard test_admin_support_progress_only_shows_own_contacts confirmed passing after Phase 51 — it was written ahead of time for this fix"

patterns-established:
  - "get_visible_user_ids() now has 3 paths: None (finance/read_only), coached-set (coach), own-set (everyone else)"

requirements-completed:
  - SCOPE-01
  - SCOPE-02

# Metrics
duration: 6min
completed: 2026-03-16
---

# Phase 51 Plan 02: Data Scoping Implementation Summary

**get_visible_user_ids() updated so admin and supervisor return {user.id} — cascades automatically to all 13 caller views, restricting both roles to own-data-only by default**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-16T13:17:13Z
- **Completed:** 2026-03-16T13:23:51Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Removed admin from the all-access branch; removed supervisor's supervised_users M2M query branch
- Finance and read_only are now the sole all-access roles (return None sentinel)
- Updated module docstring and function docstring to accurately describe new behavior
- Turned 2 RED tests (admin, supervisor) GREEN — all 6 test_permissions.py tests now pass
- Updated the breaking test in test_m2m_assignments.py to assert Phase 51 supervisor behavior
- Verified test_admin_support_progress_only_shows_own_contacts (written ahead of time) passes
- Confirmed 15 pre-existing failures are unrelated to Phase 51 and documented them

## Task Commits

Each task was committed atomically:

1. **Task 1: Update get_visible_user_ids() — admin and supervisor return {user.id}** - `f287e7f` (feat)
2. **Task 2: Update breaking test in test_m2m_assignments.py + verify full suite green** - `af9eb9a` (fix)

**Plan metadata:** (docs: complete plan — see final commit)

## Files Created/Modified
- `apps/core/permissions.py` - Removed admin/supervisor all-access branches; updated docstrings
- `apps/users/tests/test_m2m_assignments.py` - Renamed and updated supervisor test to assert {sup.id} only

## Decisions Made
- Admin and supervisor no longer have explicit branches in `get_visible_user_ids()`. They fall through to the final `return {user.id}` alongside missionary. This is the simplest correct implementation — coach is the only role needing its own branch (M2M query for coached_users).
- 15 test failures observed in full suite run were all pre-existing (confirmed by running the suite before commit `f287e7f`). They are in contacts, gifts, imports, insights apps and are unrelated to the permissions change. Documented in `deferred-items.md`, not fixed per scope-boundary rule.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- Full suite showed 15 failures but all were pre-existing (16 failures before Phase 51, 15 after — Phase 51 fixed exactly 1 of them: the supervisor M2M test). Confirmed by running `pytest --no-cov -q` on the stashed (pre-change) state.

## User Setup Required
None - no external service configuration required.

## Self-Check: PASSED

- apps/core/permissions.py: FOUND
- apps/users/tests/test_m2m_assignments.py: FOUND
- 51-02-SUMMARY.md: FOUND
- Commit f287e7f: FOUND
- Commit af9eb9a: FOUND

## Next Phase Readiness
- Phase 51 complete: admin and supervisor now default to own data across all 13 view callers
- Phase 52 (View As backend) can now build the middleware that temporarily re-enables cross-user access for admin/supervisor when a View As session is active
- The `visible is None` check in all 13 caller views remains correct — Phase 52 will set the viewed-as user on the request so the function returns {viewed_user.id}

---
*Phase: 51-data-scoping-admin-supervisor-default-to-own-data*
*Completed: 2026-03-16*
