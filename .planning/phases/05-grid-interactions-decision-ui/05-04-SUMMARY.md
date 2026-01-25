---
phase: 05-grid-interactions-decision-ui
plan: 04
subsystem: ui
tags: [react, typescript, radix, popover, toast, sonner]

# Dependency graph
requires:
  - phase: 05-01
    provides: Toast infrastructure (sonner) and UI dependencies
  - phase: 05-02
    provides: NextStep backend API
provides:
  - NextStep types, API functions, and React Query hooks
  - Stage transition warning system (checkStageTransition)
  - NextStepsCell component with popover checklist
  - Enhanced StageCell with movement warnings
affects: [05-05, phase-06]

# Tech tracking
tech-stack:
  added: ["@radix-ui/react-popover"]
  patterns: ["Optimistic updates for checklist toggle", "Lazy data loading on popover open"]

key-files:
  created:
    - frontend/src/components/ui/popover.tsx
    - frontend/src/pages/journals/components/NextStepsCell.tsx
  modified:
    - frontend/src/types/journals.ts
    - frontend/src/api/journals.ts
    - frontend/src/hooks/useJournals.ts
    - frontend/src/pages/journals/components/StageCell.tsx
    - frontend/src/pages/journals/components/index.ts

key-decisions:
  - "getHighestStageWithEvents helper determines current stage for transition warnings"
  - "Lazy loading NextSteps only when popover opens (enabled: isOpen)"
  - "Stage warnings via toast.warning - non-blocking per JRN-05"

patterns-established:
  - "Popover for inline checklist management"
  - "Optimistic toggle with rollback on error"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 5 Plan 4: Stage Warnings & NextSteps Frontend Summary

**Stage movement warnings via toast and NextStepsCell component with popover checklist using @radix-ui/react-popover**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T04:50:54Z
- **Completed:** 2026-01-25T04:54:44Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- NextStep types, API functions, and hooks with optimistic updates
- Stage transition detection with checkStageTransition function
- StageCell enhanced with warning toasts for non-sequential movement
- NextStepsCell popover with checkbox toggle, add, and delete

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NextStep types, API functions, and hooks** - `1ac3b20` (feat)
2. **Task 2: Enhance StageCell with movement warnings** - `013d01b` (feat)
3. **Task 3: Create NextStepsCell component** - `5d1ef40` (feat)

## Files Created/Modified
- `frontend/src/types/journals.ts` - NextStep types, STAGE_ORDER, checkStageTransition function
- `frontend/src/api/journals.ts` - NextStep API functions (get, create, update, delete)
- `frontend/src/hooks/useJournals.ts` - NextStep hooks with optimistic toggle
- `frontend/src/pages/journals/components/StageCell.tsx` - Movement warnings, getHighestStageWithEvents helper
- `frontend/src/components/ui/popover.tsx` - Radix popover wrapper component
- `frontend/src/pages/journals/components/NextStepsCell.tsx` - Checklist popover component
- `frontend/src/pages/journals/components/index.ts` - Barrel exports

## Decisions Made
- getHighestStageWithEvents helper determines current stage by scanning from next_steps down to contact
- Lazy loading NextSteps only when popover opens (enabled: isOpen) for performance
- Stage warnings via toast.warning - always proceed, no hard block (per JRN-05)
- Popover component from @radix-ui/react-popover with shadcn styling

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed @radix-ui/react-popover**
- **Found during:** Task 3 (NextStepsCell component)
- **Issue:** Popover component didn't exist, package not installed
- **Fix:** Ran `npm install @radix-ui/react-popover`, created popover.tsx component
- **Files modified:** package.json, package-lock.json, frontend/src/components/ui/popover.tsx
- **Verification:** TypeScript compiles, component renders
- **Committed in:** 5d1ef40 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was noted in plan as possible requirement. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- NextStep frontend integration complete
- Stage movement warnings active
- Ready for JournalGrid integration in 05-05

---
*Phase: 05-grid-interactions-decision-ui*
*Completed: 2026-01-25*
