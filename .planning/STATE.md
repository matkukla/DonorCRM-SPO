# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-12)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems.
**Current focus:** v1.2 Admin Analytics Dashboard - Phase 18 Interactive Visualizations & Drill-Down

## Current Position

Milestone: v1.2 Admin Analytics Dashboard
Phase: 19 of 19 (Advanced Features - Export & Data Tools)
Plan: 01 of 02
Status: In progress
Last activity: 2026-02-15 - Completed 19-01-PLAN.md (Backend Foundation - Date Filtering & CSV Export)

Progress: [██████████░░░░░░░░░░] 82% (v1.2 - 14/~17 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 53 (24 v1.0 + 15 v1.1 + 14 v1.2)
- Average duration: 4.2 minutes
- Total execution time: 3.9 hours

**By Milestone:**

| Milestone | Plans | Total | Avg/Plan |
|-----------|-------|-------|----------|
| v1.0 (Phases 1-6) | 24 | 1.4 hours | 2.8 min |
| v1.1 (Phases 7-12) | 15 | 76m 43s | 5.1 min |
| v1.2 (Phases 13-19) | 14 | 94m 32s | 6.8 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**Architecture for v1.2:**
- Extend existing `insights` app (not new app) for admin analytics endpoints
- Reuse journal pipeline for conversion funnel visualization
- Backend-first build order: permissions/optimization → endpoints → frontend → features
- Address critical pitfalls from research: N+1 queries, permission bypass, race conditions

**Key patterns established:**
- Django/DRF backend, React/TypeScript frontend
- Owner-scoped data with admin visibility
- Recharts for all visualizations
- Tailwind CSS + Radix UI components
- F() expressions for atomic numeric updates (13-01)
- select_for_update() for row-level locking during recalculation (13-01)
- DRF permission classes over manual role checks (13-01)
- Database-level aggregation using annotate/aggregate/Subquery (13-02)
- Admin service functions without user parameter for cross-user aggregation (13-02)
- Subquery annotation pattern for correlated queries (13-02, 14-01, 14-02)
- DRF serializers for read-only response formatting and validation (14-01)
- Safe query parameter parsing with bounded defaults (14-01, 14-02)
- Expression-based sorting with Coalesce for null-safe ordering (14-02)
- Hierarchical React Query keys for admin analytics: ['insights', 'admin', 'endpoint-name'] (15-01)
- Stub page components for incremental feature development (15-01)
- Admin sub-navigation pattern (Users, Import Center, Analytics) with NavLink active state (15-02)
- Loading/error state handling pattern for admin analytics pages (15-02)
- Currency formatting (cents to dollars) and date formatting for admin analytics (15-02)
- Client-side table sorting with TanStack Table getSortedRowModel for small datasets (16-02)
- Extracted alert computation functions for separation of concerns and testability (16-02)
- Severity-based color styling (red/amber/blue) for coaching alerts (16-02)
- TruncWeek aggregation for weekly time-series data (16-01)
- Normalize datetime/date objects from TruncWeek for consistent mapping (16-01)
- Zero-filled week list pattern for complete time series (16-01)
- Recharts FunnelChart with useMemo data transformation for proper chart format (16-03)
- Multi-line LineChart with isAnimationActive={false} to avoid dashboard sluggishness (16-03)
- Independent widget loading pattern: each widget manages its own data fetching (16-03)
- Responsive dashboard grid: lg:grid-cols-2 for charts, lg:grid-cols-3 with col-span for activity+alerts (16-03)
- Server-side pagination: pageIndex state, computed offset, pageCount from total_count (17-01)
- Sort toggle logic: same column toggles direction, new column resets to desc (17-01)
- Pagination reset on sort change: setPageIndex(0) in handleSortChange (17-01)
- Loading state differentiation: isLoading for initial load, isFetching for control disabling (17-01)
- User-scoped service functions follow team endpoint patterns with user_id parameter (17-02)
- Detail pages load data independently (metrics, trends, journals) for better UX (17-02)
- Progress indicators show ratio format (X/Y active) instead of percentage (17-02)
- Recharts onClick handler pattern for interactive chart drill-downs (18-01)
- TanStack Query enabled option for conditional data fetching (prevents eager loading) (18-01)
- Local component state (useState) for transient drill-down UI (not URL state) (18-01)
- Radix UI Sheet slide-in panels for drill-down details with accessibility built-in (18-01)
- Quick View button pattern for rapid inspection without navigation (18-02)
- Conditional column rendering with useMemo for table performance (18-02)
- Visual prominence (amber highlighting) for actionable metrics (18-02)
- Cents-to-dollars currency formatting at display time (18-02)
- Date range parameter parsing with try/except datetime.strptime validation (19-01)
- StreamingHttpResponse with csv.writer and Echo pseudo-buffer for large exports (19-01)
- Dynamic CSV filename generation with date range inclusion (19-01)
- Support limit=None in service functions for full dataset exports (19-01)
- TruncDate aggregation for daily activity heatmap data (19-01)

### Pending Todos

None yet.

### Blockers/Concerns

**Resolved in Phase 13:**
- ✅ Standardize role checks (inconsistent use of is_staff vs role=='admin') - FIXED in 13-01
- ✅ Fix race conditions in update_giving_stats() and record_fulfillment() - FIXED in 13-01
- ✅ Establish query optimization patterns (<20 queries per endpoint) - DONE in 13-02
- ✅ 5 admin analytics endpoints created with tests - DONE in 13-02

**Resolved in Phase 14:**
- ✅ Fix N+1 query problem in get_user_performance() - FIXED in 14-01
- ✅ Add missing conversion_rate field to user metrics - DONE in 14-01
- ✅ Add DRF serializers for consistent response formatting - DONE in 14-01
- ✅ Fix days_stalled for zero-activity contacts - DONE in 14-02
- ✅ Add sorting support to stalled contacts endpoint - DONE in 14-02
- ✅ Comprehensive test coverage for Phase 14 enhancements - DONE in 14-02

**Remaining:**
- Fix float arithmetic in pledge monthly_equivalent property (follow-up)
- Fix existing permission bypass vulnerability (ListAPIView only checks has_object_permission) - future phase

**Research Findings:**
- Edge Case Audit identified 16 issues; several directly impact admin analytics
- Signal skip mechanism now available for bulk imports (13-01)

## Session Continuity

Last session: 2026-02-15
Stopped at: Completed 19-01-PLAN.md (Backend Foundation - Date Filtering & CSV Export)
Resume file: None

---

*Last updated: 2026-02-15 (Phase 19 in progress, 19-01 complete)*
