---
phase: 42-mission-supervisor-role
plan: 01
subsystem: auth
tags: [django, rbac, permissions, supervisor, user-model]

# Dependency graph
requires: []
provides:
  - "MISSION_SUPERVISOR role choice in UserRole TextChoices"
  - "supervisor self-referencing FK on User model"
  - "get_visible_user_ids() centralized visibility helper"
  - "IsSupervisorWriteRestricted permission class"
  - "supervised_user_ids write field on UserAdminUpdateSerializer"
  - "supervised_users read field on CurrentUserSerializer"
affects: [42-02, 42-03, 42-04, 42-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "get_visible_user_ids() returns None for all-access roles, set of IDs for scoped roles"
    - "IsSupervisorWriteRestricted traverses owner/contact/journal chain for object-level write checks"
    - "supervised_user_ids ListField for admin batch-assignment of supervised users"

key-files:
  created:
    - "apps/users/migrations/0004_mission_supervisor_role.py"
  modified:
    - "apps/users/models.py"
    - "apps/core/permissions.py"
    - "apps/users/serializers.py"
    - "apps/users/views.py"

key-decisions:
  - "supervisor field as self-referencing FK with SET_NULL, not a separate model"
  - "get_visible_user_ids returns None sentinel for all-access roles instead of querying all user IDs"
  - "supervised_user_ids uses batch update (clear then assign) rather than incremental add/remove"
  - "supervisor field on UserSerializer is safe because endpoints are admin-gated (IsAdmin permission)"

patterns-established:
  - "Visibility helper pattern: get_visible_user_ids(user) returns None or set of UUIDs"
  - "Object-level write restriction: IsSupervisorWriteRestricted traverses owner chain"

requirements-completed: [SUPV-01, SUPV-02]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 42 Plan 01: Backend Role & Permissions Summary

**Mission Supervisor role with self-referencing supervisor FK, centralized visibility helper, and write-restricted permission class**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T17:30:01Z
- **Completed:** 2026-03-02T17:33:40Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- MISSION_SUPERVISOR added as fifth role in UserRole TextChoices with migration 0004 applied
- get_visible_user_ids() helper centralizes per-role data visibility scoping for all 5 roles
- IsSupervisorWriteRestricted permission class enforces read-only on supervised data with owner chain traversal
- UserAdminUpdateSerializer supports supervised_user_ids for batch assignment of supervised users
- CurrentUserSerializer returns supervised_users list for supervisor role users

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Mission Supervisor role, supervisor FK, and migration** - `2ebcec6` (feat)
2. **Task 2: Add visibility helper, permission class, and serializer updates** - `8671cf9` (feat)

## Files Created/Modified
- `apps/users/models.py` - Added MISSION_SUPERVISOR role, supervisor FK, is_mission_supervisor property, updated can_view_contact
- `apps/users/migrations/0004_mission_supervisor_role.py` - Migration adding supervisor FK and altering role field
- `apps/core/permissions.py` - Added get_visible_user_ids() helper, IsSupervisorWriteRestricted class, updated IsStaffOrAbove
- `apps/users/serializers.py` - Added supervised_user_ids to UserAdminUpdateSerializer, supervised_users to CurrentUserSerializer, supervisor to UserSerializer
- `apps/users/views.py` - Updated UserListCreateView and UserDetailView to prefetch supervised_users

## Decisions Made
- supervisor field as self-referencing FK with SET_NULL -- keeps relationship simple and allows clean cleanup
- get_visible_user_ids returns None sentinel for all-access roles -- avoids expensive query for admin/finance/read_only
- supervised_user_ids uses batch update (clear then assign) rather than incremental add/remove -- simpler API contract
- supervisor field on UserSerializer is safe because endpoints are admin-gated (IsAdmin permission) -- no conditional hiding needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Role and permission infrastructure complete, ready for view-level queryset scoping (Plan 02)
- get_visible_user_ids() helper ready for use in all list views
- IsSupervisorWriteRestricted ready to be added to view permission_classes

## Self-Check: PASSED

All 6 files verified present. Both commit hashes (2ebcec6, 8671cf9) found in git log.

---
*Phase: 42-mission-supervisor-role*
*Completed: 2026-03-02*
