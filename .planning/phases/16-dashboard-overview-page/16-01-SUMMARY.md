---
phase: 16-dashboard-overview-page
plan: 01
subsystem: api
tags: [django, drf, react-query, typescript, recharts, time-series]

# Dependency graph
requires:
  - phase: 13-backend-permissions-optimization
    provides: Admin service function pattern (cross-user aggregation)
  - phase: 14-admin-analytics-enhancements
    provides: DRF serializers and safe query parameter parsing
  - phase: 15-frontend-foundation-routing
    provides: React Query hierarchical key pattern for admin analytics
provides:
  - Team trends endpoint returning 12-week time-series data
  - TruncWeek aggregation pattern for weekly metrics
  - Frontend types and hook for trend chart data
affects: [17-dashboard-summary-cards, 18-dashboard-trend-charts, 19-dashboard-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TruncWeek aggregation for weekly time-series data
    - Normalize datetime/date objects from TruncWeek for consistent mapping
    - Zero-filled week list for complete time series

key-files:
  created:
    - apps/insights/tests/test_team_trends.py
  modified:
    - apps/insights/services.py
    - apps/insights/serializers.py
    - apps/insights/views.py
    - apps/insights/urls.py
    - frontend/src/api/insights.ts
    - frontend/src/hooks/useInsights.ts

key-decisions:
  - "Use TruncWeek for weekly aggregation with 12-week default window"
  - "Normalize datetime/date objects from TruncWeek to handle DateField vs DateTimeField differences"
  - "Start weeks on Monday following ISO week standard"

patterns-established:
  - "TruncWeek aggregation: Separate queries per metric, combine via maps"
  - "Zero-fill pattern: Build complete week list filling gaps from query results"
  - "Date normalization: Handle both datetime and date objects from TruncWeek"

# Metrics
duration: 5m 33s
completed: 2026-02-14
---

# Phase 16 Plan 01: Team Trends Endpoint & Frontend Data Layer Summary

**Weekly time-series endpoint aggregating decisions, donations, and stage progressions over 12 weeks using TruncWeek with React Query hook**

## Performance

- **Duration:** 5m 33s
- **Started:** 2026-02-14T16:46:07Z
- **Completed:** 2026-02-14T16:51:40Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created GET /api/v1/insights/admin/team-trends/ endpoint returning 12 weekly data points
- Implemented database-level aggregation using TruncWeek for decisions, donations, and stage events
- Added comprehensive test coverage (12 tests) verifying admin access, data structure, counts, and parameter handling
- Created TypeScript types and React Query hook for frontend integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create team trends backend endpoint** - `86ef475` (feat)
2. **Task 2: Add frontend types and hook** - `0fe3bcc` (feat)

## Files Created/Modified
- `apps/insights/services.py` - Added get_team_trends() service function with TruncWeek aggregation
- `apps/insights/serializers.py` - Added TrendDataPointSerializer and TeamTrendsResponseSerializer
- `apps/insights/views.py` - Added TeamTrendsView APIView with admin-only access
- `apps/insights/urls.py` - Added admin/team-trends/ URL pattern
- `apps/insights/tests/test_team_trends.py` - Created comprehensive test suite (12 tests)
- `frontend/src/api/insights.ts` - Added TrendDataPoint, TeamTrendsResponse types and getAdminTeamTrends function
- `frontend/src/hooks/useInsights.ts` - Added useAdminTeamTrends React Query hook

## Decisions Made

**1. TruncWeek aggregation approach**
- Rationale: Three separate queries (decisions, donations, stage events) aggregated by week, then combined via dictionaries for efficient lookup. Follows established pattern from get_donations_by_month.

**2. Date normalization for TruncWeek results**
- Rationale: TruncWeek on DateTimeField returns datetime objects, on DateField returns date objects. Added normalize_to_date() helper to handle both cases consistently.

**3. ISO week standard (Monday start)**
- Rationale: Django TruncWeek defaults to Monday-start weeks (ISO standard). Aligns with international business convention and simplifies week boundary calculations.

**4. 12-week default with 1-52 bounds**
- Rationale: 12 weeks provides ~3 months of trend visibility without overwhelming chart. Max 52 weeks allows annual view if needed. Bounded via get_safe_int_param for security.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Decision model field usage in tests**
- **Found during:** Task 1 test creation
- **Issue:** Test attempted to create Decision with non-existent decision_type field
- **Fix:** Updated test to use actual Decision model fields (amount, cadence, status) per model definition
- **Files modified:** apps/insights/tests/test_team_trends.py
- **Verification:** All 12 tests pass
- **Committed in:** 86ef475 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed PipelineStage enum values in tests**
- **Found during:** Task 1 test creation
- **Issue:** Test referenced non-existent PipelineStage values (CONTACT_MADE, APPOINTMENT_SCHEDULED, CALL_COMPLETED)
- **Fix:** Updated to use actual enum values (CONTACT, MEET, CLOSE) from PipelineStage model
- **Files modified:** apps/insights/tests/test_team_trends.py
- **Verification:** Stage progression test passes
- **Committed in:** 86ef475 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs - incorrect model field/enum usage)
**Impact on plan:** Both fixes were test code corrections to match actual model definitions. No production code changes. No scope creep.

## Issues Encountered

**TruncWeek datetime vs date handling**
- Problem: TruncWeek on DateTimeField (created_at) returns datetime, on DateField (date) returns date. Initial code assumed all datetime.
- Solution: Added normalize_to_date() helper function to handle both types consistently.
- Impact: Service function works correctly with mixed field types.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 02 (Dashboard Summary Cards):**
- Team trends endpoint fully tested and working
- Frontend hook available for data fetching
- Time-series data structure established

**Ready for Plan 03 (Dashboard Trend Charts):**
- TrendDataPoint interface matches Recharts data requirements
- Weekly labels formatted for chart display
- Zero-filled weeks ensure consistent chart rendering

**No blockers or concerns.**

---
*Phase: 16-dashboard-overview-page*
*Completed: 2026-02-14*
