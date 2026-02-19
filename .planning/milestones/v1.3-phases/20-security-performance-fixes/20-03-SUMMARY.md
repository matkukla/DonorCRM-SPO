---
phase: 20-security-performance-fixes
plan: 03
subsystem: api, ui
tags: [django, drf, prefetch, n+1, performance, react, useEffect, side-effects]

# Dependency graph
requires:
  - phase: 10-pipeline-journal
    provides: "JournalContact, JournalStageEvent, Decision models and serializers"
  - phase: 20-security-performance-fixes-01
    provides: "Owner-scoped querysets and cross-user contact validation"
provides:
  - "Prefetch-optimized journal grid queryset (3 queries instead of ~400)"
  - "Python-based aggregation in serializer using prefetched data"
  - "POST /dashboard/mark-seen/ endpoint for marking events as seen"
  - "Side-effect-free dashboard GET endpoint"
affects: [23-journal-filters, dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Prefetch with to_attr for N+1 elimination", "Python grouping over prefetched data instead of per-row DB queries", "useRef guard for one-time POST after data load"]

key-files:
  created: []
  modified:
    - apps/journals/views.py
    - apps/journals/serializers.py
    - apps/dashboard/views.py
    - apps/dashboard/urls.py
    - frontend/src/api/dashboard.ts
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "Skipped visual indicators for unseen events -- is_new field has no current visual distinction; decoupling the marking from GET is the core fix"
  - "Used getattr fallback pattern so serializer works both with and without prefetch (single object vs. list)"

patterns-established:
  - "Prefetch+to_attr pattern: use Prefetch(queryset=..., to_attr='prefetched_X') in view, getattr(obj, 'prefetched_X', None) in serializer"
  - "Side-effect-free GET: move write operations to separate POST endpoints, call from frontend useEffect after render"

# Metrics
duration: 5min
completed: 2026-02-17
---

# Phase 20 Plan 03: N+1 Query Fix & Dashboard Side Effect Decoupling Summary

**Prefetch-optimized journal grid (400 queries down to 3) with Python-based aggregation, and decoupled mark-events-as-seen into POST /dashboard/mark-seen/ endpoint**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-17T16:01:41Z
- **Completed:** 2026-02-17T16:07:39Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- JournalContactListCreateView queryset now uses Prefetch with to_attr for stage_events and decisions, reducing journal grid from ~400 queries to 3 (QAL-05)
- JournalContactSerializer.get_stage_events() and get_decision() use Python aggregation over prefetched data with fallback for non-prefetched access
- DashboardView.get() no longer calls mark_events_as_not_new (no GET side effects, QAL-09)
- New MarkEventsSeenView POST endpoint at /dashboard/mark-seen/ for explicit event marking
- Dashboard.tsx calls markEventsSeen() once per mount via useEffect + useRef after data loads

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix N+1 queries in journal grid with prefetch and Python aggregation (QAL-05)** - `8a21549` (fix)
2. **Task 2: Decouple mark-events-as-seen from dashboard GET into separate POST endpoint (QAL-09)** - `bd205b8` (feat)

## Files Created/Modified
- `apps/journals/views.py` - Added Prefetch import and prefetch_related with to_attr in JournalContactListCreateView.get_queryset()
- `apps/journals/serializers.py` - Rewrote get_stage_events() and get_decision() to use prefetched data with Python grouping
- `apps/dashboard/views.py` - Removed mark_events_as_not_new from DashboardView.get(), added MarkEventsSeenView POST endpoint
- `apps/dashboard/urls.py` - Added mark-seen/ URL pattern and MarkEventsSeenView import
- `frontend/src/api/dashboard.ts` - Added markEventsSeen() API function
- `frontend/src/pages/Dashboard.tsx` - Added useEffect with useRef guard to call markEventsSeen after data loads

## Decisions Made
- Skipped visual indicators for unseen events -- the is_new field has no current visual distinction in the frontend. The core fix is decoupling marking from GET. Visual indicators can be added in a future phase if requested.
- Used getattr fallback pattern so the serializer works both with prefetched list views and without prefetch for single object retrieval.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- QAL-05 (N+1 fix) complete -- prerequisite for journal filters (Phase 23) is met
- QAL-09 (dashboard side effect) complete -- dashboard GET is now pure
- All Phase 20 plans complete (3/3) -- security & performance fixes phase is done
- Ready to proceed to Phase 21 (django-filter setup) and subsequent filter phases

## Self-Check: PASSED

- All 6 modified files exist on disk
- Commit `8a21549` found (Task 1)
- Commit `bd205b8` found (Task 2)
- SUMMARY.md created at expected path
- 73 tests passing across journals (54) and dashboard (19)
- TypeScript compiles clean (no errors)

---
*Phase: 20-security-performance-fixes*
*Completed: 2026-02-17*
