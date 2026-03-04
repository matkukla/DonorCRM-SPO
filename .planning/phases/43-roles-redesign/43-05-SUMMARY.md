---
phase: 43-roles-redesign
plan: 05
subsystem: ui
tags: [react, typescript, react-query, shadcn-ui, tabs, table]

requires:
  - phase: 43-roles-redesign plan 01
    provides: supervised_users field in auth context for supervisor and coach roles
  - phase: 43-roles-redesign plan 03
    provides: My Team nav item and sidebar routing to /team and /team/:userId

provides:
  - TeamPage at /team: searchable list of supervised missionaries with View Profile buttons
  - MissionaryProfilePage at /team/:userId: read-only tabbed profile with Contacts/Journals/Tasks/Donations
  - Authorization guard: 403 state when userId not in supervised_users
  - Coach-aware: Donations tab hidden for coach role

affects:
  - future supervisor/coach UX improvements

tech-stack:
  added: []
  patterns:
    - "Client-side search filter on supervised_users from auth context (no extra API call)"
    - "React hooks called unconditionally with empty params when not authorized (Rules of Hooks)"
    - "owner param passed to useContacts/useJournals/useTasks/useGifts for cross-missionary data"

key-files:
  created: []
  modified:
    - frontend/src/pages/team/TeamPage.tsx
    - frontend/src/pages/team/MissionaryProfilePage.tsx

key-decisions:
  - "MissionaryProfilePage derives missionary data from supervised_users in auth context — no extra getUser() call needed"
  - "Coach role check hides Donations tab and skips useGifts fetch by passing empty params"
  - "Hooks called unconditionally with empty params when hasAccess=false to satisfy Rules of Hooks"
  - "Gifts use donor_contact_name and amount_dollars fields (not contact_name/amount) per Gift interface"
  - "Journals tab shows goal_amount column (JournalListItem has no member_count field)"

requirements-completed: []

duration: 5min
completed: 2026-03-04
---

# Phase 43 Plan 05: My Team Page + Missionary Profile Page Summary

**TeamPage with client-side search and MissionaryProfilePage with Contacts/Journals/Tasks/Donations tabs, role-based authorization, and coach-aware Donations tab hiding**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-04T22:04:39Z
- **Completed:** 2026-03-04T22:09:50Z
- **Tasks:** 4 (including TypeScript check)
- **Files modified:** 2

## Accomplishments
- Replaced TeamPage card stub with searchable table matching plan spec (Name/Email/Action columns)
- Built MissionaryProfilePage with full tabbed profile: Contacts, Journals, Tasks, Donations
- Authorization guard rejects non-supervised missionaries with 403-style state
- Donations tab correctly absent for coach role, present for supervisor

## Task Commits

1. **Task 1: TeamPage** - `c1cb191` (feat)
2. **Task 2: MissionaryProfilePage** - `2488a84` (feat)
3. **Task 3: Directory structure** - `16a7d10` (chore — already existed)
4. **Task 4: TypeScript check** - `e35f8cf` (chore — clean pass)

## Files Created/Modified
- `frontend/src/pages/team/TeamPage.tsx` - Searchable table with role-aware subtitle and View Profile links
- `frontend/src/pages/team/MissionaryProfilePage.tsx` - Tabbed read-only profile with owner-filtered data fetching

## Decisions Made
- Used `supervised_users` from auth context to find missionary data instead of calling `useUser()` — avoids extra API call and provides the authorization check in one step
- `useGifts` receives empty `{}` params when user is coach — results in empty query key, data never fetched
- All 4 data hooks called unconditionally (React Rules of Hooks) — pass empty `{}` when not authorized so query fires but returns no meaningful data
- Fixed stub's incorrect field references: `gift.contact_name` → `gift.donor_contact_name`, `gift.amount` → `gift.amount_dollars`
- `JournalListItem` has no `member_count` field — used `goal_amount` column instead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected Gift field names in Donations tab**
- **Found during:** Task 2 (MissionaryProfilePage implementation)
- **Issue:** Initial draft used `gift.contact_name` and `gift.amount` which don't exist on the `Gift` interface
- **Fix:** Changed to `gift.donor_contact_name` and `gift.amount_dollars` per `src/api/gifts.ts`
- **Files modified:** `frontend/src/pages/team/MissionaryProfilePage.tsx`
- **Verification:** `npx tsc --noEmit` passes clean
- **Committed in:** 2488a84

**2. [Rule 1 - Bug] Removed non-existent member_count from JournalListItem**
- **Found during:** Task 2 (Journals tab implementation)
- **Issue:** Plan stub referenced `journal.member_count` but `JournalListItem` type has no such field
- **Fix:** Used `goal_amount` column instead for the journals table
- **Files modified:** `frontend/src/pages/team/MissionaryProfilePage.tsx`
- **Verification:** `npx tsc --noEmit` passes clean
- **Committed in:** 2488a84

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes required for TypeScript correctness. No scope creep.

## Issues Encountered
None — all data APIs already supported `owner` filter parameter from Phase 42 backend work.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- My Team page and Missionary Profile page are feature-complete
- Phase 43 (Roles Redesign) is now complete — all 5 plans shipped
- v2.2 milestone (UI Polish, Journal Report & Supervisor Role) fully delivered

---
*Phase: 43-roles-redesign*
*Completed: 2026-03-04*
