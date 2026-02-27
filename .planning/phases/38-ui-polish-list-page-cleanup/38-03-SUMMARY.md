---
phase: 38-ui-polish-list-page-cleanup
plan: 03
subsystem: ui, api
tags: [react, django, cleanup, analytics, heatmap]

# Dependency graph
requires:
  - phase: 38-01
    provides: "Dialog conversion and donation list polish"
  - phase: 38-02
    provides: "Review Queue removal already completed as part of Prospect rename commit"
provides:
  - "Clean removal of Activity Heatmap backend, frontend, and npm package"
  - "Review Queue redirect from /insights/review-queue to /admin/analytics/dashboard"
  - "Reduced frontend bundle size by removing @uiw/react-heat-map"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Route redirect pattern for removed features (Navigate with replace)"
tech-stack-removed:
  - "@uiw/react-heat-map"

key-files:
  created: []
  modified:
    - "apps/insights/views.py"
    - "apps/insights/urls.py"
    - "apps/insights/services.py"
    - "apps/insights/serializers.py"
    - "frontend/src/api/insights.ts"
    - "frontend/src/hooks/useInsights.ts"
    - "frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx"
    - "frontend/package.json"
  deleted:
    - "frontend/src/pages/insights/ReviewQueue.tsx"
    - "frontend/src/pages/admin/analytics/components/ActivityHeatmap.tsx"

key-decisions:
  - "Review Queue removal was already done in plan 02 commit 31c8e8c (included in Prospect rename); no duplicate commit needed"
  - "Cleaned up unused TruncDate import from services.py after heatmap removal"

patterns-established: []

requirements-completed: [ANLY-01, ANLY-02]

# Metrics
duration: 7min
completed: 2026-02-27
---

# Phase 38 Plan 03: Remove Review Queue and Activity Heatmap Summary

**Full removal of Review Queue feature and Activity Heatmap from backend and frontend, including @uiw/react-heat-map package uninstall**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-27T16:59:52Z
- **Completed:** 2026-02-27T17:06:50Z
- **Tasks:** 2
- **Files modified:** 10 (plus 2 deleted)

## Accomplishments
- Review Queue fully removed: backend view/service/URL, frontend page/hook/API/sidebar/route (with redirect to analytics dashboard)
- Activity Heatmap fully removed: backend view/service/URL/serializers, frontend component/hook/API/dashboard JSX
- @uiw/react-heat-map uninstalled from package.json, reducing bundle size
- All Django and TypeScript checks pass clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove Review Queue** - `31c8e8c` (already completed in plan 02)
2. **Task 2: Remove Activity Heatmap** - `27419bd` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `apps/insights/views.py` - Removed ActivityHeatmapView class and imports
- `apps/insights/urls.py` - Removed activity-heatmap URL path
- `apps/insights/services.py` - Removed get_activity_heatmap function and unused TruncDate import
- `apps/insights/serializers.py` - Removed ActivityHeatmapDaySerializer and ActivityHeatmapResponseSerializer
- `frontend/src/api/insights.ts` - Removed ActivityHeatmap types and getAdminActivityHeatmap function
- `frontend/src/hooks/useInsights.ts` - Removed useAdminActivityHeatmap hook
- `frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx` - Removed ActivityHeatmap import and JSX
- `frontend/package.json` - Removed @uiw/react-heat-map dependency
- `frontend/src/pages/admin/analytics/components/ActivityHeatmap.tsx` - DELETED
- `frontend/src/pages/insights/ReviewQueue.tsx` - DELETED (in plan 02)

## Decisions Made
- Review Queue removal was already completed as part of plan 02 commit `31c8e8c` (bundled with Prospect-to-Potential-Donor rename). No duplicate commit was created for Task 1.
- Cleaned up unused `TruncDate` import from services.py that was only used by the removed `get_activity_heatmap` function.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Cleanup] Removed unused TruncDate import**
- **Found during:** Task 2 (Activity Heatmap removal)
- **Issue:** `TruncDate` was imported in services.py but only used by the now-deleted `get_activity_heatmap` function
- **Fix:** Removed `TruncDate` from the import line
- **Files modified:** apps/insights/services.py
- **Verification:** Django check passes, no remaining uses of TruncDate
- **Committed in:** 27419bd (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 cleanup)
**Impact on plan:** Minimal - removing unused import is standard cleanup after feature deletion.

**Note:** Task 1 (Review Queue removal) was already completed in plan 02 commit `31c8e8c`. All changes were already in the codebase. This is not a deviation but a sequencing overlap from the prior plan execution.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 38 (UI Polish & List Page Cleanup) is now complete with all 3 plans executed
- All unused analytics features removed, codebase is cleaner
- Ready for Phase 39

## Self-Check: PASSED

- 38-03-SUMMARY.md: FOUND
- ReviewQueue.tsx deleted: CONFIRMED
- ActivityHeatmap.tsx deleted: CONFIRMED
- Commit 27419bd (Task 2): FOUND
- Commit 31c8e8c (Task 1, plan 02): FOUND

---
*Phase: 38-ui-polish-list-page-cleanup*
*Completed: 2026-02-27*
