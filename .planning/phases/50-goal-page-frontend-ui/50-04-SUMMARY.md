---
phase: 50-goal-page-frontend-ui
plan: 04
subsystem: ui
tags: [react, goal, progress-bar, pacing, read-only, lazy-route, shadcn]

# Dependency graph
requires:
  - phase: 50-goal-page-frontend-ui
    plan: 01
    provides: "Backend event-sourced calls_count and meetings_count in goal API response"
  - phase: 50-goal-page-frontend-ui
    plan: 02
    provides: "GoalProgressBar component with support/default color variants and tick marks"
  - phase: 50-goal-page-frontend-ui
    plan: 03
    provides: "useGoalData, useUpdateGoal hooks; GoalData, GoalUpdatePayload types; goals API client"

provides:
  - "GoalPage.tsx — complete goal page with three cards: Goal Settings, Progress, Pacing Targets"
  - "Sidebar Goal nav entry at index 1 (after Dashboard, before Contacts) with Target icon"
  - "Lazy-loaded /goal route in App.tsx with ProtectedPage wrapper"
  - "Pacing Targets card with 4 stat tiles computed from Partners-based formula"
  - "Read-only mode for supervisor/admin: inputs disabled, Save hidden, banner shown"
  - "Empty state handling: no_goal and no_journals prompts on Support bar"
  - "Milestone motivational messages on Monthly Support bar by 25% thresholds"

affects:
  - Phase 51 (data scoping) — GoalPage reads goalData which uses useGoalData hook
  - Phase 52-53 (View As) — GoalPage isReadOnly check may need View As awareness

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PacingTile as inline sub-component (not separate file) for simple co-located UI"
    - "PACING_CONFIG constants at file top-level (outside component) for shared pacing math"
    - "useEffect to sync local form state from API data on load (goalData dependency)"
    - "fmt() helper for null-safe number display returning '—' for null values"
    - "settingsSaved flag with 3-second setTimeout for transient save feedback"

key-files:
  created:
    - frontend/src/pages/goal/GoalPage.tsx
  modified:
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/App.tsx

key-decisions:
  - "GoalPage.tsx includes all three cards (Settings, Progress, Pacing) in a single file — no sub-component files, keeps the page self-contained"
  - "Pacing values (partnersNeeded, callsNeeded, convosNeeded, apptsNeeded, apptsPerWeek) computed at component top-level so both Progress card bars and Pacing Targets card share them without duplication"
  - "calls_count and meetings_count are read-only server-computed values — no input fields rendered, displayed as plain text count labels only"
  - "Journal checkbox list fetches via useJournals({ page_size: '100' }) to avoid pagination truncation; uses data?.results ?? []"

patterns-established:
  - "Goal page pacing: Partners formula — partnersNeeded = ceil(goalDollars / 80), then multiply by per-partner constants for calls/appts"
  - "Empty state: no_goal when monthly_support_goal_cents === 0; no_journals when selected_journal_ids.length === 0"
  - "Read-only guard: const isReadOnly = user?.role === 'supervisor' || user?.role === 'admin'"

requirements-completed: [GOAL-01, GOAL-05, GOAL-06, GOAL-07, GOAL-08, GOAL-09, GOAL-10]

# Metrics
duration: 6min
completed: 2026-03-14
---

# Phase 50 Plan 04: Goal Page Frontend Summary

**Complete Goal page with Goal Settings card, read-only Progress bars from server event counts, Partners-formula pacing tiles, and supervisor/admin read-only enforcement wired to live API data**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-14T01:21:10Z
- **Completed:** 2026-03-14T01:27:33Z
- **Tasks:** 3
- **Files modified:** 3 created/modified

## Accomplishments
- Sidebar now shows "Goal" nav entry at index 1 (between Dashboard and Contacts) with Target icon
- /goal route lazy-loads GoalPage with ProtectedPage wrapper; no role restriction — all roles see it, read-only enforcement is in-page
- Goal Settings card: monthly goal (dollars), weeks, journal checkbox list, Save Settings button with success feedback — all disabled for supervisor/admin with read-only banner
- Progress card: three GoalProgressBar bars — Monthly Support (colorVariant=support with red/green/amber thresholds), Calls/Convos, Appointments — activity counts are read-only from server (no input fields)
- Pacing Targets card: 4 tiles (Partners Needed, Calls Needed, Appointments Needed, Appointments/Week) computed via Partners formula; descriptive text below; all show "—" when no goal set
- Empty states: "Set a goal amount above..." when no goal; "Select journals above..." when no journals
- All 8 backend tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Goal nav link and lazy route** - `822073a` (feat)
2. **Task 2: Build Goal Settings card and Progress card** - `b6bd2e1` (feat)
3. **Task 3: Build Pacing Targets card and wire full page** - `b6bd2e1` (feat, same commit — both cards implemented in one GoalPage.tsx file)

**Plan metadata:** (docs commit pending)

## Files Created/Modified
- `frontend/src/pages/goal/GoalPage.tsx` - Complete goal page with all three cards, pacing logic, read-only mode, empty states
- `frontend/src/components/layout/Sidebar.tsx` - Added Target icon import; Goal navItem at index 1
- `frontend/src/App.tsx` - Added GoalPage lazy import; /goal route after / and before /contacts

## Decisions Made
- GoalPage built as a single file with inline PacingTile sub-component — page is self-contained, no need to split into sub-files at this complexity level
- Pacing values computed at component top-level so Progress bars and Pacing Targets card both reference the same derived numbers without duplication
- `React` import removed — project uses react-jsx transform (jsx pragma not needed in file scope)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused React import causing TS6133 error**
- **Found during:** Task 3 (build verification)
- **Issue:** `import React, { useState, useEffect } from "react"` — React was unused under react-jsx transform
- **Fix:** Changed to `import { useState, useEffect } from "react"`
- **Files modified:** frontend/src/pages/goal/GoalPage.tsx
- **Verification:** `npx tsc --noEmit` passes clean; no TS6133 error
- **Committed in:** b6bd2e1

---

**Total deviations:** 1 auto-fixed (1 bug — unused import)
**Impact on plan:** Trivial fix. No scope creep.

## Issues Encountered

Pre-existing `npm run build` (`tsc -b`) failures in 5 unrelated files existed before any 50-04 changes. Logged in `deferred-items.md`. These are out of scope:
- `UserDetail.tsx`: missing `monthlyAverage` prop (phase 48 regression)
- `ContactList.tsx`, `DonationList.tsx`: unused `isAdmin` variable
- `StageCell.tsx`: two unused parameter errors

`npx tsc --noEmit` passes clean. All backend goal tests (8) pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Goal page is complete and functional — all three cards, read-only enforcement, live API data
- Phase 50 Plan 05 can proceed (if any remaining plans exist)
- Phase 51 (data scoping) will need to ensure GoalPage's useGoalData still returns correct data under the new scoping rules
- Phase 52-53 (View As) may need isReadOnly to also account for View As context

---
*Phase: 50-goal-page-frontend-ui*
*Completed: 2026-03-14*
