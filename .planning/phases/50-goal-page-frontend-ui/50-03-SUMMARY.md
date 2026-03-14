---
phase: 50-goal-page-frontend-ui
plan: 03
subsystem: api
tags: [react-query, typescript, axios, goals]

# Dependency graph
requires:
  - phase: 50-01
    provides: calls_count/meetings_count computed by backend GoalView from JournalStageEvent FK chain
  - phase: 49-04
    provides: GET /api/v1/goals/me/ and PATCH /api/v1/goals/me/ endpoints

provides:
  - GoalData TypeScript interface (8 fields, server-computed fields clearly annotated)
  - GoalUpdatePayload TypeScript interface (partial, journal_ids write key)
  - getGoal() typed API function (GET /goals/me/)
  - updateGoal() typed API function (PATCH /goals/me/, returns GoalData)
  - useGoalData() React Query hook (queryKey: ["goal"])
  - useUpdateGoal() React Query mutation hook (setQueryData on success)

affects:
  - 50-04 (GoalPage.tsx wiring — imports these modules)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "API client module pattern: typed interfaces + async functions wrapping apiClient"
    - "setQueryData on mutation success instead of invalidateQueries to avoid stale flash"
    - "Separate read/write keys: selected_journal_ids (GET) vs journal_ids (PATCH)"

key-files:
  created:
    - frontend/src/api/goals.ts
    - frontend/src/hooks/useGoal.ts
  modified: []

key-decisions:
  - "GoalUpdatePayload excludes calls_count/meetings_count — server-computed from JournalStageEvent, not writable via PATCH"
  - "useUpdateGoal uses setQueryData(['goal'], data) not invalidateQueries to avoid stale-cache round-trip flash"
  - "Write key is journal_ids (not selected_journal_ids) matching backend PATCH contract"

patterns-established:
  - "goals.ts: follows mpd.ts structure — JSDoc comments, typed interfaces, separate interface per direction (read/write)"
  - "useGoal.ts: follows useMPD.ts structure — named exports, queryKey array literals"

requirements-completed: [GOAL-01, GOAL-06, GOAL-09, GOAL-10]

# Metrics
duration: 1min
completed: 2026-03-14
---

# Phase 50 Plan 03: Goal API Client and React Query Hooks Summary

**Typed goals.ts API module + useGoal.ts React Query hooks wiring GET/PATCH /api/v1/goals/me/ with direct cache update on mutation**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-14T01:18:19Z
- **Completed:** 2026-03-14T01:19:06Z
- **Tasks:** 2
- **Files modified:** 2 (created)

## Accomplishments
- GoalData interface with all 8 backend fields; calls_count/meetings_count annotated as read-only server-computed
- GoalUpdatePayload interface with correct PATCH write keys (journal_ids, not selected_journal_ids)
- getGoal() and updateGoal() following mpd.ts patterns with full generics
- useGoalData() and useUpdateGoal() following useMPD.ts patterns; mutation uses setQueryData to skip refetch round-trip

## Task Commits

Each task was committed atomically:

1. **Task 1: Create goals.ts API client module** - `4fc120f` (feat)
2. **Task 2: Create useGoal.ts React Query hooks** - `0600fba` (feat)

## Files Created/Modified
- `frontend/src/api/goals.ts` - GoalData/GoalUpdatePayload interfaces, getGoal(), updateGoal() functions
- `frontend/src/hooks/useGoal.ts` - useGoalData() and useUpdateGoal() React Query hooks

## Decisions Made
- GoalUpdatePayload excludes calls_count/meetings_count because they are derived server-side from JournalStageEvent records — the backend ignores them on PATCH even if sent, but we exclude them to make the contract explicit
- useUpdateGoal uses setQueryData(["goal"], data) instead of invalidateQueries — the PATCH response already returns the full updated GoalData, so there is no need for a follow-up GET
- Write key for journals is journal_ids on PATCH vs selected_journal_ids on GET — follows backend contract documented in 50-CONTEXT.md

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- frontend/src/api/goals.ts and frontend/src/hooks/useGoal.ts are ready for import by Plan 04 (GoalPage.tsx)
- TypeScript compiles clean; no blocking issues

---
*Phase: 50-goal-page-frontend-ui*
*Completed: 2026-03-14*
