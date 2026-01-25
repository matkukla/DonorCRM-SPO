---
phase: 06-reporting-integration
plan: 02
subsystem: api
tags: [django, drf, recharts, shadcn-ui, foreign-key, charts]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Task model structure
  - phase: 01-foundation
    provides: Journal model structure
provides:
  - Task.journal optional ForeignKey for journal-specific tasks
  - TaskSerializer journal read/write with ownership validation
  - shadcn/ui Chart component primitives for reporting
affects: [06-reporting-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional ForeignKey pattern (null=True, blank=True) for cross-model linking"
    - "Serializer-level ownership validation for related entities"
    - "shadcn/ui chart components wrapping Recharts"

key-files:
  created:
    - frontend/src/components/ui/chart.tsx
  modified:
    - apps/tasks/models.py
    - apps/tasks/serializers.py
    - apps/tasks/migrations/0003_add_journal_fk.py

key-decisions:
  - "Optional journal FK on Task model (null=True, blank=True) - enables journal-specific tasks without requiring all tasks to be journal-linked"
  - "CASCADE delete for journal tasks - when journal deleted, its tasks are deleted (appropriate for journal-specific context)"
  - "Serializer-level ownership validation for journal field - follows existing pattern from Decision/JournalContact"
  - "Manual chart component creation over shadcn CLI - project lacks components.json but has existing shadcn components"

patterns-established:
  - "Optional cross-model relationships via ForeignKey with null=True, blank=True"
  - "Index on (foreign_key, status) for efficient filtered queries"

# Metrics
duration: 5min
completed: 2026-01-25
---

# Phase 06 Plan 02: Task-Journal Link + Chart Component Summary

**Task model extended with optional journal FK, TaskSerializer handles journal read/write with ownership validation, shadcn/ui Chart component ready for reporting**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-25T05:47:29Z
- **Completed:** 2026-01-25T05:52:30Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Task model extended with optional journal ForeignKey (null=True, blank=True)
- Added index on (journal, status) for efficient filtering
- TaskSerializer updated with journal PrimaryKeyRelatedField and ownership validation
- shadcn/ui Chart component installed with ChartContainer, ChartConfig, ChartTooltip, ChartLegend
- TypeScript types fixed for Recharts integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Add journal ForeignKey to Task model** - `c0638db` (feat) - *Note: Completed in prior execution*
2. **Task 2: Update TaskSerializer to include journal field** - `cdcbb50` (feat)
3. **Task 3: Install shadcn/ui Chart component** - `723f466` (feat)

## Files Created/Modified
- `apps/tasks/models.py` - Added optional journal ForeignKey with CASCADE delete and (journal, status) index
- `apps/tasks/migrations/0003_add_journal_fk.py` - Migration adding journal_id column and indexes
- `apps/tasks/serializers.py` - Added journal PrimaryKeyRelatedField, journal_name read-only field, and validate_journal ownership check
- `frontend/src/components/ui/chart.tsx` - Created Chart component with ChartContainer, ChartConfig, ChartTooltip, ChartLegend (wraps Recharts)

## Decisions Made
- **Optional journal FK:** null=True, blank=True allows tasks to exist independently of journals
- **CASCADE delete:** When journal deleted, its tasks are deleted (appropriate - journal tasks are journal-specific)
- **Serializer ownership validation:** validate_journal ensures journal.owner == request.user (follows Decision/JournalContact pattern)
- **Manual chart component:** Created chart.tsx manually instead of using shadcn CLI (project lacks components.json)
- **Fixed TypeScript types:** Added explicit type annotations for payload and legend props to resolve Recharts type inference issues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed TypeScript type errors in chart component**
- **Found during:** Task 3 (Chart component installation)
- **Issue:** Recharts type inference failed for payload and legend props, causing build errors
- **Fix:** Added explicit type annotations: `payload?: any[]`, `labelFormatter?: (value: any, payload: any) => React.ReactNode`, etc.
- **Files modified:** frontend/src/components/ui/chart.tsx
- **Verification:** npm run build passes with no chart.tsx errors
- **Committed in:** 723f466 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** TypeScript type fix necessary for build to pass. No scope creep.

## Issues Encountered
- Project missing components.json despite having existing shadcn components - created chart.tsx manually following existing component pattern
- Recharts TypeScript types required explicit annotations for tooltip/legend payload props

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Task model ready for journal-specific tasks (JRN-17)
- Chart component primitives ready for Report tab implementation (JRN-15)
- No blockers for next plans

---
*Phase: 06-reporting-integration*
*Completed: 2026-01-25*
