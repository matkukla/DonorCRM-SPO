---
phase: 06-reporting-integration
plan: 04
status: complete
wave: 2
subsystem: frontend-analytics
tags: [react, tanstack-query, recharts, analytics, charts, ui]

requires:
  - phase: 06-reporting-integration
    plan: 01
    provides: Analytics API endpoints
  - phase: 06-reporting-integration
    plan: 02
    provides: Chart component infrastructure

provides:
  - Report tab chart components
  - Analytics query hooks
  - Four visualization components (DecisionTrendsChart, StageActivityChart, PipelineBreakdownChart, NextStepsQueue)

affects:
  - future-plans: Report tab integration (will use these components)
  - future-plans: Dashboard analytics (can reuse these charts)

tech-stack:
  added:
    - recharts components: BarChart, AreaChart, PieChart
    - date-fns: formatDistanceToNow for next steps queue
  patterns:
    - TanStack Query hooks for analytics with 5-minute staleTime
    - Hierarchical query keys: ['journals', 'analytics', <metric>]
    - Loading and empty state handling in chart components
    - Memoized chart data transformations

key-files:
  created:
    - frontend/src/pages/journals/components/ReportCharts.tsx: Four chart/list components with loading/empty states
  modified:
    - frontend/src/types/journals.ts: Analytics data types
    - frontend/src/api/journals.ts: Analytics API functions
    - frontend/src/hooks/useJournals.ts: Analytics query hooks
    - frontend/src/pages/journals/components/index.ts: Export analytics components

decisions:
  - decision: Type-only import for ChartConfig
    rationale: verbatimModuleSyntax requires type imports to use "import type"
    impact: Prevents TypeScript compilation errors
    alternatives: Disable verbatimModuleSyntax (not recommended for modern TS)
  - decision: 5-minute staleTime for analytics charts, 2 minutes for next-steps-queue
    rationale: Analytics data doesn't change every second, can tolerate slight staleness; next steps more time-sensitive
    impact: Reduces API load, improves perceived performance
    alternatives: Lower staleTime for real-time updates (unnecessary for analytics)
  - decision: Pie chart label via props.index to access chartData
    rationale: Recharts PieLabelRenderProps doesn't include data properties, need index to access
    impact: Enables custom labels with name and count
    alternatives: Use default label rendering (less informative)

metrics:
  duration: 4 minutes
  completed: 2026-01-24
---

# Phase 6 Plan 4: Report Tab UI with Chart Components

**One-liner:** Report tab chart components with TanStack Query hooks for decision trends, stage activity, pipeline breakdown, and next steps queue.

## Overview

Built four chart/list components for the Report tab analytics: DecisionTrendsChart (bar), StageActivityChart (area), PipelineBreakdownChart (pie), and NextStepsQueue (list). All components use TanStack Query hooks with appropriate caching (5-minute staleTime for charts, 2 minutes for next steps queue) and handle loading/empty states.

## Tasks Completed

### Task 1: Add analytics types and API functions
**Files:** `frontend/src/types/journals.ts`, `frontend/src/api/journals.ts`
**Commit:** a24a71e

Added TypeScript types for analytics data:
- `DecisionTrendItem`: month + count for bar chart
- `StageActivityItem`: date + per-stage counts for area chart
- `PipelineBreakdownItem`: stage + count for pie chart
- `NextStepsQueueItem`: task details with contact/journal context

Added API functions:
- `getDecisionTrends()`: Fetch monthly decision counts
- `getStageActivity()`: Fetch stage event counts over time
- `getPipelineBreakdown()`: Fetch current stage distribution
- `getNextStepsQueue()`: Fetch pending next steps across all contacts

All API functions return strongly-typed data matching Django serializers.

### Task 2: Add analytics React Query hooks
**Files:** `frontend/src/hooks/useJournals.ts`
**Commit:** 15f49a2

Created TanStack Query hooks with hierarchical cache keys:
- `useDecisionTrends()`: ['journals', 'analytics', 'decision-trends']
- `useStageActivity()`: ['journals', 'analytics', 'stage-activity']
- `usePipelineBreakdown()`: ['journals', 'analytics', 'pipeline-breakdown']
- `useNextStepsQueue()`: ['journals', 'analytics', 'next-steps-queue']

Cache strategy:
- 5-minute staleTime for charts (data doesn't change rapidly)
- 2-minute staleTime for next steps (more time-sensitive)
- Enables bulk invalidation: `queryClient.invalidateQueries({ queryKey: ['journals', 'analytics'] })`

### Task 3: Create ReportCharts component with all charts
**Files:** `frontend/src/pages/journals/components/ReportCharts.tsx`, `frontend/src/pages/journals/components/index.ts`
**Commit:** b19b512

Built four components:

**DecisionTrendsChart (bar chart):**
- Shows decision count by month
- Handles loading with skeleton
- Handles empty state with message
- Uses ChartContainer with decisionTrendsConfig

**StageActivityChart (area chart):**
- Stacked area chart showing events by stage over time
- Six areas (contact, meet, close, decision, thank, next_steps)
- Color-coded using chart CSS variables (--chart-1 through --chart-6)

**PipelineBreakdownChart (pie chart):**
- Shows current stage distribution
- Labels show both stage name and count
- Uses useMemo for data transformation (adds fill colors and names)
- Pie chart label uses props.index to access chartData (Recharts typing limitation)

**NextStepsQueue (list):**
- Shows pending next steps across all contacts
- Displays contact name, journal name, and due date
- Badge color: destructive if overdue, secondary if upcoming
- Uses formatDistanceToNow for relative dates

All components:
- Export from index.ts for easy imports
- Handle loading states with skeletons
- Handle empty states with user-friendly messages
- Use shadcn/ui Card components for consistent styling

## Verification Results

- [x] Analytics types exported from @/types/journals
- [x] API functions exported from @/api/journals
- [x] Query hooks exported from @/hooks/useJournals
- [x] ReportCharts.tsx compiles without TypeScript errors
- [x] pnpm build succeeds (only unused import warnings)
- [x] Components handle loading and empty states
- [x] Components importable from @/pages/journals/components

## Deviations from Plan

None - plan executed exactly as written.

## Technical Decisions

**Type-only import for ChartConfig:**
- Found during TypeScript compilation
- TypeScript's verbatimModuleSyntax requires `import type` for type-only imports
- Changed `import { ChartConfig }` to `import type { ChartConfig }`
- Alternative: disable verbatimModuleSyntax (not recommended for modern TypeScript)
- Impact: Clean type imports, prevents runtime bundling of type-only dependencies

**Pie chart label via props.index:**
- Found during TypeScript compilation
- Recharts PieLabelRenderProps doesn't include data properties
- Solution: use `props.index` to access original chartData
- Alternative: use default label rendering (less informative)
- Impact: Enables custom labels showing both stage name and count

## Success Criteria Met

All success criteria met:
- DecisionTrendsChart renders bar chart with decision trends
- StageActivityChart renders area chart with stage activity
- PipelineBreakdownChart renders pie chart with pipeline breakdown
- NextStepsQueue renders list with next steps queue
- All components use TanStack Query hooks with appropriate caching (5 minutes for charts, 2 minutes for next steps)
- All components handle loading and empty states
- Components ready for Report tab integration

## Next Phase Readiness

**Blockers:** None

**Recommendations:**
- Integrate charts into Report tab UI (likely next plan)
- Add filtering/date range controls for analytics views
- Consider adding export functionality for analytics data

**Dependencies satisfied:**
- Analytics API endpoints (06-01) implemented
- Chart component infrastructure (06-02) installed
- All four chart components ready for integration

## Key Files Reference

**Created:**
- `/home/matkukla/projects/DonorCRM/frontend/src/pages/journals/components/ReportCharts.tsx` - 230 lines, four chart/list components

**Modified:**
- `/home/matkukla/projects/DonorCRM/frontend/src/types/journals.ts` - Added analytics data types (4 interfaces)
- `/home/matkukla/projects/DonorCRM/frontend/src/api/journals.ts` - Added analytics API functions (4 functions)
- `/home/matkukla/projects/DonorCRM/frontend/src/hooks/useJournals.ts` - Added analytics query hooks (4 hooks)
- `/home/matkukla/projects/DonorCRM/frontend/src/pages/journals/components/index.ts` - Export analytics components

## Lessons Learned

**What worked well:**
- TanStack Query hooks pattern consistent with existing hooks
- Chart components handle loading/empty states gracefully
- Memoized data transformations prevent unnecessary re-renders
- Hierarchical query keys enable efficient cache invalidation

**Challenges encountered:**
- TypeScript verbatimModuleSyntax requires type-only imports
- Recharts PieLabelRenderProps typing doesn't include data properties

**For future phases:**
- Consider adding TypeScript helper types for Recharts label props
- Document staleTime strategy for different data types (analytics vs operational data)
