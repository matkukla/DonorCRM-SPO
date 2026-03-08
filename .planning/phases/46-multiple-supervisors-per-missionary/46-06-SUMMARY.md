---
phase: 46-multiple-supervisors-per-missionary
plan: 06
subsystem: api
tags: [django, m2m, assignments, role-filter, management-command]

# Dependency graph
requires:
  - phase: 46-multiple-supervisors-per-missionary
    provides: M2M supervisors/coaches fields on User model and AssignmentsView API
provides:
  - Role-filtered AssignmentsView GET: supervisor_ids/coach_ids only returns active users holding correct role
  - purge_ghost_assignments management command for removing stale M2M junction rows
  - 4 regression tests for ghost supervisor/coach filtering in AssignmentsView GET
affects:
  - Assignments UI (frontend) — no longer shows ghost supervisor/coach entries

# Tech tracking
tech-stack:
  added: []
  patterns:
    - M2M role filtering: m.supervisors.filter(role='supervisor', is_active=True) pattern applied in AssignmentsView GET
    - Management command for data cleanup: apps/users/management/commands/ package

key-files:
  created:
    - apps/users/management/__init__.py
    - apps/users/management/commands/__init__.py
    - apps/users/management/commands/purge_ghost_assignments.py
  modified:
    - apps/users/views_assignments.py
    - apps/users/tests/test_m2m_assignments.py

key-decisions:
  - "Role filter applied in GET view (not serializer) — closest to the data access point, cheapest fix"
  - "Ghost rows detected by User.objects.filter(...).update() in tests to bypass User.save() auto-clear — true reproduction of migration ghost rows"
  - "purge_ghost_assignments does not auto-detect admin-created reassignments: only removes users whose role no longer matches the M2M relationship type"

patterns-established:
  - "Queryset filtering on M2M relations: m.supervisors.filter(role='supervisor', is_active=True) — apply role+activity guards at the query level, not Python"
  - "Ghost row test setup: User.objects.filter(id=x).update(role='new_role') bypasses save() hooks to simulate migration artifacts"

requirements-completed: [SUPV-02]

# Metrics
duration: 10min
completed: 2026-03-07
---

# Phase 46 Plan 06: Ghost Supervisor Filter Summary

**Role-filtered AssignmentsView GET and purge_ghost_assignments management command closing UAT gap #9 — ghost M2M rows no longer returned in supervisor/coach ID lists**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-07T00:00:00Z
- **Completed:** 2026-03-07T00:10:00Z
- **Tasks:** 2 (Task 1 = TDD: RED commit + GREEN commit)
- **Files modified:** 5

## Accomplishments
- Fixed `AssignmentsView GET` to filter `m.supervisors.all()` → `m.supervisors.filter(role='supervisor', is_active=True)` and same for coaches
- Added `TestAssignmentsViewRoleFilter` with 4 regression tests: ghost supervisor excluded, ghost coach excluded, active supervisor included, inactive supervisor excluded
- Created `purge_ghost_assignments` Django management command with `--dry-run` support to remove stale M2M rows left by migration 0006

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing role-filter regression tests** - `1279fae` (test)
2. **Task 1 GREEN: Fix role filter in AssignmentsView GET** - `6df1b81` (fix)
3. **Task 2: Create purge_ghost_assignments management command** - `a068204` (feat)

## Files Created/Modified
- `apps/users/views_assignments.py` - Changed .supervisors.all() and .coaches.all() to filter by role and is_active
- `apps/users/tests/test_m2m_assignments.py` - Added TestAssignmentsViewRoleFilter with 4 regression tests
- `apps/users/management/__init__.py` - Package init (new)
- `apps/users/management/commands/__init__.py` - Package init (new)
- `apps/users/management/commands/purge_ghost_assignments.py` - Management command to remove ghost M2M rows (new)

## Decisions Made
- Applied role filter at the queryset level in the view (not serializer layer) — closest to the data access point, no downstream side effects
- Used `User.objects.filter(id=x).update(role='missionary')` in tests to bypass `User.save()` auto-clear signal, creating true ghost rows that replicate migration 0006 artifacts
- Management command reports counts with `self.style.SUCCESS` for clear output, supports `--dry-run` for safe preview

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures (unrelated to this plan) found in full suite run:
- `test_models.py::TestUserModel::test_role_properties` — references `is_staff_role` attribute removed in Phase 43
- `test_views.py::TestUserListView::test_admin_can_create_user` — uses old `staff` role string (replaced in Phase 43)

These were pre-existing before this plan's changes. Deferred per scope boundary rules (out-of-scope pre-existing failures).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UAT gap #9 is now closed: AssignmentsView GET no longer returns ghost supervisor/coach entries
- purge_ghost_assignments command can be run on production to clean any stale rows from the original M2M migration
- All 10 tests in test_m2m_assignments.py pass

---
*Phase: 46-multiple-supervisors-per-missionary*
*Completed: 2026-03-07*
