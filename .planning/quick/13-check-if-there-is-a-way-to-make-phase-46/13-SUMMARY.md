---
phase: quick-13
plan: 01
subsystem: testing, ui
tags: [pytest, react, react-router, typescript, admin]

# Dependency graph
requires:
  - phase: 43-roles-redesign
    provides: UserRole enum with missionary/supervisor/coach/admin/finance/read_only values
  - phase: 46-multiple-supervisors-per-missionary
    provides: AdminAssignments M2M assignments page with dirty tracking
provides:
  - Fixed test_role_properties using current role properties (is_missionary, is_supervisor, is_coach)
  - Fixed test_admin_can_create_user using valid 'read_only' role string
  - AdminAssignments sticky Save bar visible at bottom when dirty.size > 0
  - AdminAssignments useBlocker navigation guard with Stay/Leave dialog
  - AdminAssignments beforeunload guard for browser tab close/refresh
affects: [phase-46, testing, admin-assignments]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - useBlocker from react-router-dom for in-app navigation guards
    - beforeunload event listener for browser-level unsaved-changes protection
    - sticky bottom-0 bar pattern for always-accessible save action on long pages

key-files:
  created: []
  modified:
    - apps/users/tests/test_models.py
    - apps/users/tests/test_views.py
    - frontend/src/pages/admin/AdminAssignments.tsx

key-decisions:
  - "Sticky save bar is additive — existing toolbar Save button kept; bottom bar provides second access point"
  - "blocker dialog placed outside Container but inside Section to avoid layout conflicts"
  - "beforeunload guard uses dirty.size dep array so it re-registers only when dirty state changes"

patterns-established:
  - "useBlocker + beforeunload dual-guard pattern for pages with local unsaved state"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-03-09
---

# Quick Task 13: Fix pre-existing failing tests and improve Assignments page UX

**Fixed two Phase-43-era broken tests (is_staff_role / 'staff' role string) and added sticky Save bar plus useBlocker navigation guard to AdminAssignments**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T14:17:54Z
- **Completed:** 2026-03-09T14:20:04Z
- **Tasks:** 2 auto tasks + 1 checkpoint (human-verify)
- **Files modified:** 3

## Accomplishments
- test_role_properties now uses existing role properties (is_missionary, is_supervisor, is_coach) — removes is_staff_role reference that was removed in Phase 43
- test_admin_can_create_user posts 'read_only' instead of removed 'staff' role string — all 21 tests in those files now pass
- AdminAssignments shows sticky bottom save bar when dirty.size > 0 so the Save button is always visible on long lists
- AdminAssignments blocks in-app React Router navigation with a confirmation dialog when there are unsaved changes
- beforeunload event listener prevents accidental tab close or browser refresh with unsaved assignments

## Task Commits

1. **Task 1: Fix pre-existing failing tests from Phase 43 role rename** - `977c0e5` (fix)
2. **Task 2: Add sticky Save bar and unsaved-changes guard to AdminAssignments** - `f49d23b` (feat)

## Files Created/Modified
- `apps/users/tests/test_models.py` - test_role_properties rewritten to use current role properties
- `apps/users/tests/test_views.py` - test_admin_can_create_user: 'staff' → 'read_only' role
- `frontend/src/pages/admin/AdminAssignments.tsx` - sticky save bar + useBlocker guard + beforeunload handler

## Decisions Made
- Kept existing toolbar Save button in place; sticky bar is purely additive
- Placed blocker dialog as last child of Section (outside Container) to avoid layout container constraints
- Used dirty.size in beforeunload dependency array so handler always reflects current state

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

The pytest coverage reporter raises a PermissionError on htmlcov/ during teardown — this is a pre-existing environment issue unrelated to the test changes. Both target tests passed correctly.

## Next Phase Readiness
- Test suite is clean for the two long-broken tests
- AdminAssignments UX improvements ready for human verification

---
*Phase: quick-13*
*Completed: 2026-03-09*
