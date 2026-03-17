---
phase: 53-view-as-frontend
plan: 02
subsystem: ui
tags: [react, typescript, context, banner, dashboard, view-as]

# Dependency graph
requires:
  - phase: 53-view-as-frontend
    plan: 01
    provides: ViewAsProvider, useViewAs hook, useViewableUsers hook, sessionStorage-backed context with setViewAsUser/exitViewAs/isViewingAs

provides:
  - ViewAsBanner component (amber banner with Eye icon, name, Exit button — renders null when not in View As)
  - AppLayout with ViewAsBanner slotted between Header and main for app-wide persistence
  - Dashboard missionary picker driven by ViewAsContext (setViewAsUser/exitViewAs) and useViewableUsers()
  - Local Dashboard read-only info banner removed

affects:
  - 53-03 (cache invalidation plan — builds on same ViewAsContext)
  - Any future page that needs to check isViewingAs for read-only guards

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ViewAsBanner returns null when isViewingAs is false — zero layout impact when inactive
    - App-level banner in AppLayout persists View As confirmation across all page navigation
    - Dashboard picker calls setViewAsUser(id, full_name) on context — single source of truth
    - useViewableUsers() replaces role-conditional useUsers()+filter pattern in picker

key-files:
  created:
    - frontend/src/components/layout/ViewAsBanner.tsx
  modified:
    - frontend/src/components/layout/AppLayout.tsx
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "isViewingOther alias removed — all guards use isViewingAs directly from context (cleaner, one canonical name)"
  - "selectedUserName kept as alias for viewAsUserName for picker trigger button display clarity"
  - "effectiveMpdData now simply equals mpdData — X-View-As-User-Id header scopes MPD data server-side, no client-side override needed"
  - "mpd-overview-table guard updated from isViewingOther to isViewingAs — admin sees all-missionaries table only on own dashboard"

patterns-established:
  - "View As banner: slot ViewAsBanner into layout wrapper (not individual pages) for persistence"
  - "View As picker: call setViewAsUser(id, full_name) directly — name stored in context, no find() derivation needed"

requirements-completed: [VIEWAS-01, VIEWAS-02, VIEWAS-03, VIEWAS-04]

# Metrics
duration: 8min
completed: 2026-03-17
---

# Phase 53 Plan 02: View As Frontend Banner and Dashboard Selector Summary

**Amber ViewAsBanner in AppLayout and Dashboard picker wired to ViewAsContext — admin/supervisor can enter/exit View As from Dashboard, banner persists across all pages**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-17T07:00:12Z
- **Completed:** 2026-03-17T07:07:02Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Created ViewAsBanner.tsx: amber banner with Eye icon, "Viewing [Name] · Read Only" text, and Exit button — renders null when inactive
- AppLayout.tsx: ViewAsBanner slotted between Header and main, making the banner persistent across all page navigation
- Dashboard.tsx: replaced 74 lines of local state logic with 15 lines driven by ViewAsContext — picker calls setViewAsUser/exitViewAs, uses useViewableUsers(), removed local info banner

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ViewAsBanner and slot into AppLayout** - `f54ca31` (feat)
2. **Task 2: Promote Dashboard selector from local state to ViewAsContext** - `dfd5506` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/components/layout/ViewAsBanner.tsx` - New amber banner component; reads isViewingAs/viewAsUserName/exitViewAs from useViewAs(); returns null when inactive
- `frontend/src/components/layout/AppLayout.tsx` - Imports ViewAsBanner; renders it between Header and main
- `frontend/src/pages/Dashboard.tsx` - Refactored to use ViewAsContext; useViewableUsers() for picker; setViewAsUser/exitViewAs for picker actions; local read-only banner removed; MPD data simplified (no client-side override)

## Decisions Made
- Removed `isViewingOther` alias entirely — all guards now use `isViewingAs` directly, removing the ambiguous synonym
- `effectiveMpdData = mpdData` directly — backend scopes MPD data via X-View-As-User-Id header, no client-side missionary lookup needed
- `mpd-overview-table` guard updated to `isViewingAs` — admin MPD overview table hidden when in View As mode (consistent with earlier phase decision)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused isViewingOther alias after substitution**
- **Found during:** Task 2 (Dashboard selector refactor)
- **Issue:** After replacing all `isViewingOther` guard conditions with `isViewingAs`, the alias `const isViewingOther = isViewingAs` became a dead declaration that TypeScript would flag
- **Fix:** Removed the dead alias; all guards already updated to use `isViewingAs` directly
- **Files modified:** frontend/src/pages/Dashboard.tsx
- **Verification:** TypeScript compile passes with no errors
- **Committed in:** dfd5506 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — dead variable removal)
**Impact on plan:** Minor cleanup necessary for correctness. No scope creep.

## Issues Encountered
None — all changes applied cleanly, TypeScript reported zero errors after each task.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 01 (ViewAsProvider + API wiring) and Plan 02 (banner + Dashboard picker) are complete
- View As mode is fully functional: enter via Dashboard picker, amber banner persists, Exit clears session
- Plan 03 (cache invalidation strategy) can proceed — ViewAsContext is stable

---
*Phase: 53-view-as-frontend*
*Completed: 2026-03-17*

## Self-Check: PASSED

All expected files and commits verified:
- frontend/src/components/layout/ViewAsBanner.tsx — FOUND
- frontend/src/components/layout/AppLayout.tsx — FOUND
- frontend/src/pages/Dashboard.tsx — FOUND
- .planning/phases/53-view-as-frontend/53-02-SUMMARY.md — FOUND
- Commit f54ca31 (Task 1) — FOUND
- Commit dfd5506 (Task 2) — FOUND
