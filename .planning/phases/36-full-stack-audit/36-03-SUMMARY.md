---
phase: 36-full-stack-audit
plan: 03
subsystem: performance
tags: [django-orm, sql-aggregation, react-lazy, code-splitting, vite, recharts, dnd-kit]

# Dependency graph
requires:
  - phase: 27-gift-recurring-gift-models
    provides: RecurringGift model with frequency choices and monthly_equivalent property
  - phase: 34-dashboard-polish
    provides: Dashboard with dnd-kit drag-and-drop tile reordering
provides:
  - SQL-based recurring gift aggregation via CASE/WHEN in dashboard services
  - _monthly_equivalent_aggregate() reusable helper for RecurringGift SQL totals
  - MPDOverviewView single-query pattern (eliminates N+1)
  - React.lazy code splitting for 12 heavy pages
  - Vite manual chunks for recharts and dnd-kit vendor splitting
  - Suspense fallback with Loader2 spinner inside AppLayout
affects: [dashboard, insights, imports, frontend-bundle]

# Tech tracking
tech-stack:
  added: []
  patterns: [SQL CASE/WHEN aggregation for frequency multipliers, React.lazy with Suspense for route-level code splitting, Vite manualChunks for vendor splitting]

key-files:
  created: []
  modified:
    - apps/dashboard/services.py
    - apps/imports/views.py
    - frontend/src/App.tsx
    - frontend/vite.config.ts

key-decisions:
  - "SQL CASE/WHEN frequency multipliers match RecurringGift.monthly_equivalent property exactly (Decimal division, not pre-computed floats)"
  - "Contact.needs_thank_you and PrayerIntention.status indexes already exist -- no migration needed"
  - "12 pages lazy-loaded (5 heavy + 2 admin analytics + 5 insights) via individual module imports, not barrel re-exports"
  - "Suspense boundary inside AppLayout so sidebar stays visible during chunk loading"

patterns-established:
  - "_monthly_equivalent_aggregate(): reusable SQL aggregation for RecurringGift monthly totals -- use this instead of Python loops"
  - "React.lazy with individual module imports (not barrel files) for proper per-page code splitting"
  - "PageLoadingFallback: centered Loader2 spinner for Suspense boundaries"

requirements-completed: [AUDIT-01]

# Metrics
duration: 7min
completed: 2026-02-24
---

# Phase 36 Plan 03: Performance Audit Summary

**SQL CASE/WHEN aggregation for dashboard recurring gift totals, MPDOverviewView N+1 elimination, and React.lazy code splitting for 12 heavy pages with Vite vendor chunking**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-24T15:28:50Z
- **Completed:** 2026-02-24T15:35:50Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Dashboard `get_support_progress()` and `get_giving_summary()` now compute monthly recurring totals via SQL CASE/WHEN aggregation instead of loading all RecurringGifts into Python (O(N) to O(1) memory)
- MPDOverviewView refactored from N+1 per-user snapshot queries to a single Subquery-based fetch (2 queries total regardless of user count)
- 12 frontend pages converted to React.lazy with Suspense fallback, producing 24 separate build chunks instead of a monolithic bundle
- Vite manualChunks splits recharts (412KB) and dnd-kit (47KB) into dedicated vendor chunks
- Verified Contact.needs_thank_you and PrayerIntention.status indexes already exist (db_index=True + Meta.indexes)

## Task Commits

Each task was committed atomically:

1. **Task 1: Optimize dashboard and insights query patterns** - `7cd29e5` (perf)
2. **Task 2: Frontend bundle optimization with React.lazy and code splitting** - `0949791` (perf, bundled with 36-01 summary commit by concurrent agent)

## Files Created/Modified
- `apps/dashboard/services.py` - Added FREQUENCY_MULTIPLIERS dict, _monthly_equivalent_aggregate() helper, replaced Python loops in get_support_progress() and get_giving_summary()
- `apps/imports/views.py` - Refactored MPDOverviewView from N+1 loop to Subquery + single batch fetch
- `frontend/src/App.tsx` - Converted 12 page imports to React.lazy, added Suspense with PageLoadingFallback, kept lightweight pages eagerly loaded
- `frontend/vite.config.ts` - Added build.rollupOptions.output.manualChunks for recharts and dnd-kit

## Decisions Made
- Used exact Decimal division for frequency multipliers (matching the `monthly_equivalent` property) rather than pre-computed float constants, ensuring numerical consistency
- Contact.needs_thank_you already has `db_index=True` on the field AND an explicit index in `Meta.indexes` -- no migration needed
- PrayerIntention.status already has `db_index=True` AND composite indexes in `Meta.indexes` -- no migration needed
- Lazy-loaded insights pages via individual module imports (`@/pages/insights/DonationsByMonthYear`) instead of barrel re-export (`@/pages/insights`) to enable proper per-page tree-shaking and code splitting
- Placed Suspense boundary inside `ProtectedPage` wrapper so the sidebar/layout stays visible while lazy chunks load

## Deviations from Plan

None - plan executed exactly as written. All indexes were already present (documented rather than added).

## Issues Encountered

- Task 2 frontend files were committed by a concurrent 36-01 agent as part of its summary commit (`0949791`). The code changes are correct and complete; only the commit attribution is non-standard.
- Three pre-existing test failures found (not caused by this plan's changes, confirmed by stash/restore testing):
  - `test_team_trends.py::test_counts_donations_by_week` -- date-sensitive test
  - `test_user_drilldown.py::test_returns_correct_stats` -- pre-existing
  - `test_services.py::TestGiftExport::test_export_gifts_csv` -- pre-existing

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend performance patterns optimized for dashboard and insights queries
- Frontend build produces well-split chunks for faster initial page loads
- Ready for code quality audit (Phase 36, Plan 04)

## Self-Check: PASSED

- All 4 modified files exist on disk
- Commit `7cd29e5` (Task 1) verified in git log
- Commit `0949791` (Task 2) verified in git log
- `apps/dashboard/services.py` contains Case/When and _monthly_equivalent_aggregate (4 matches)
- `apps/imports/views.py` contains Subquery/OuterRef (5 matches)
- `frontend/src/App.tsx` contains 13 React.lazy references and 4 Suspense references
- `frontend/vite.config.ts` contains manualChunks configuration
- Frontend build produces 24 separate chunks (verified)

---
*Phase: 36-full-stack-audit*
*Completed: 2026-02-24*
