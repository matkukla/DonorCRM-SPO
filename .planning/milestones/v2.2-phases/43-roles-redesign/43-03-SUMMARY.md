---
phase: 43-roles-redesign
plan: 3
subsystem: ui
tags: [react, typescript, roles, permissions, coach, supervisor, missionary]

requires:
  - phase: 43-01
    provides: Backend role rename migration (staff→missionary, mission_supervisor→supervisor, coach added)
  - phase: 43-02
    provides: Backend API endpoints for assignments, coach FK on User model

provides:
  - TypeScript UserRole type with renamed roles (missionary, supervisor, coach)
  - Assignment API types and functions (MissionaryAssignment, AssignmentsData, AssignmentUpdate)
  - Updated ProtectedRoute roleHierarchy with coach at level 3
  - Sidebar with My Team nav item (visible to supervisor/coach only) and Assignments admin link
  - App.tsx routes for /admin/assignments, /team, /team/:userId
  - AdminUsers coach picker and coached_user_ids support
  - AdminAssignments page for bulk supervisor/coach assignment
  - TeamPage and MissionaryProfilePage stub pages
  - All list/detail pages updated: canSeeOwner and ownerOptions include coach
  - ContactDetail hides Donations/Pledges tabs for coach viewing non-owned contacts

affects: [43-04, 43-05, all frontend pages with role checks]

tech-stack:
  added: []
  patterns:
    - "visibleRoles array on NavItem for exact role match (vs requiredRole hierarchy comparison)"
    - "showFinancialTabs pattern for coach tab visibility based on contact ownership"

key-files:
  created:
    - frontend/src/pages/admin/AdminAssignments.tsx
    - frontend/src/pages/team/TeamPage.tsx
    - frontend/src/pages/team/MissionaryProfilePage.tsx
  modified:
    - frontend/src/api/users.ts
    - frontend/src/api/auth.ts
    - frontend/src/components/auth/ProtectedRoute.tsx
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/App.tsx
    - frontend/src/pages/admin/AdminUsers.tsx
    - frontend/src/hooks/useUsers.ts
    - frontend/src/pages/contacts/ContactList.tsx
    - frontend/src/pages/contacts/ContactDetail.tsx
    - frontend/src/pages/donations/DonationList.tsx
    - frontend/src/pages/donations/DonationDetail.tsx
    - frontend/src/pages/pledges/PledgeList.tsx
    - frontend/src/pages/journals/JournalList.tsx
    - frontend/src/pages/tasks/TaskList.tsx
    - frontend/src/pages/prayer/PrayerList.tsx
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "visibleRoles takes priority over requiredRole in canAccess() — used for My Team item (supervisor/coach exact match, not hierarchy)"
  - "showFinancialTabs computed from isCoach + contact ownership — hides Donations/Pledges tabs for coach viewing non-owned contacts"
  - "useAssignments and useUpdateAssignments hooks added to useUsers.ts (colocation with user query pattern)"
  - "AdminAssignments uses local overrides state pattern — shows pending changes before bulk save"

requirements-completed: []

duration: 7min
completed: 2026-03-04
---

# Phase 43 Plan 3: Frontend Types + Mechanical Role Rename Summary

**TypeScript role system renamed (staff→missionary, mission_supervisor→supervisor, coach added), with assignment API types, new pages (AdminAssignments, TeamPage, MissionaryProfilePage), and coach role checks across all 8 list/detail pages.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-04T21:54:58Z
- **Completed:** 2026-03-04T22:01:38Z
- **Tasks:** 9
- **Files modified:** 19 (16 modified + 3 created)

## Accomplishments

- Updated `UserRole` type union and `userRoleLabels` across entire frontend codebase
- Added `MissionaryAssignment`, `AssignmentsData`, `AssignmentUpdate` types and API functions
- Updated roleHierarchy in ProtectedRoute and Sidebar to `{admin:5, supervisor:4, coach:3, finance:3, missionary:2, read_only:1}`
- Added "My Team" nav item visible only to supervisor/coach roles using new `visibleRoles` pattern
- Added `AdminAssignments` page with bulk supervisor/coach assignment UI
- Added `TeamPage` and `MissionaryProfilePage` stubs accessible to supervisor/coach
- Mechanical sweep of 8 list/detail pages — coach now gets canSeeOwner=true and owner dropdown
- ContactDetail hides financial tabs (Donations, Pledges) for coach viewing non-owned contacts
- TypeScript check passes with zero errors

## Task Commits

All tasks committed atomically in one commit:

1. **Tasks 1-9: All frontend role rename + new pages** - `26ff762` (feat)

## Files Created/Modified

- `frontend/src/api/users.ts` - New UserRole, assignment types/functions, coach field on User
- `frontend/src/api/auth.ts` - Updated role union, added coach field
- `frontend/src/components/auth/ProtectedRoute.tsx` - Updated role union + hierarchy
- `frontend/src/components/layout/Sidebar.tsx` - visibleRoles pattern, My Team item, Assignments link
- `frontend/src/App.tsx` - New lazy imports + routes, role strings renamed
- `frontend/src/pages/admin/AdminUsers.tsx` - roleVariants, coach picker, Assignments sub-nav
- `frontend/src/pages/admin/AdminAssignments.tsx` - New bulk assignments page
- `frontend/src/pages/team/TeamPage.tsx` - New team overview page
- `frontend/src/pages/team/MissionaryProfilePage.tsx` - New missionary profile stub
- `frontend/src/hooks/useUsers.ts` - useAssignments and useUpdateAssignments hooks
- 8 list/detail pages - canSeeOwner/ownerOptions/isReadOnly updated to include coach

## Decisions Made

- `visibleRoles` array on NavItem for exact role match (vs hierarchy) — used for My Team (supervisor/coach only, not admin by hierarchy)
- `showFinancialTabs` computed from `isCoach` + contact ownership — hides Donations/Pledges tabs for coach viewing non-owned contacts
- `useAssignments`/`useUpdateAssignments` hooks added to `useUsers.ts` (colocation with user query pattern)
- AdminAssignments uses local `overrides` state for pending changes before bulk save

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All frontend types aligned with new role names
- AdminAssignments, TeamPage, MissionaryProfilePage stubs created and routed
- TypeScript passes cleanly — ready for 43-04 (backend assignments API implementation)
- coach role fully propagated across all permission checks

---
*Phase: 43-roles-redesign*
*Completed: 2026-03-04*
