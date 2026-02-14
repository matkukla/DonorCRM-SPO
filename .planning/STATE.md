# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-12)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems.
**Current focus:** v1.2 Admin Analytics Dashboard - Phase 16 Dashboard Overview Page

## Current Position

Milestone: v1.2 Admin Analytics Dashboard
Phase: 16 of 19 (Dashboard Overview Page)
Plan: 16-03 complete
Status: Phase 16 complete
Last activity: 2026-02-14 - Completed 16-03-PLAN.md (Dashboard Overview Page)

Progress: [████████░░░░░░░░░░░░] 57% (v1.2 - 8/~14 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 47 (24 v1.0 + 15 v1.1 + 8 v1.2)
- Average duration: 3.4 minutes
- Total execution time: 3.1 hours

**By Milestone:**

| Milestone | Plans | Total | Avg/Plan |
|-----------|-------|-------|----------|
| v1.0 (Phases 1-6) | 24 | 1.4 hours | 2.8 min |
| v1.1 (Phases 7-12) | 15 | 76m 43s | 5.1 min |
| v1.2 (Phases 13-19) | 8 | 36m 7s | 4.5 min |

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

Last session: 2026-02-14
Stopped at: Completed 16-03-PLAN.md (Dashboard Overview Page)
Resume file: None

---

*Last updated: 2026-02-14 (16-03 complete - Phase 16 complete)*
