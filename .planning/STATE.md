# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-12)

**Core value:** Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems.
**Current focus:** v1.2 Admin Analytics Dashboard - Phase 15 Frontend Foundation & Routing

## Current Position

Milestone: v1.2 Admin Analytics Dashboard
Phase: 15 of 19 (Frontend Foundation & Routing)
Plan: 1 of ~4
Status: In progress
Last activity: 2026-02-13 - Completed 15-01-PLAN.md (Data Layer & Routes)

Progress: [████░░░░░░░░░░░░░░░░] 36% (v1.2 - 5/~14 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 44 (24 v1.0 + 15 v1.1 + 5 v1.2)
- Average duration: 3.4 minutes
- Total execution time: 2.9 hours

**By Milestone:**

| Milestone | Plans | Total | Avg/Plan |
|-----------|-------|-------|----------|
| v1.0 (Phases 1-6) | 24 | 1.4 hours | 2.8 min |
| v1.1 (Phases 7-12) | 15 | 76m 43s | 5.1 min |
| v1.2 (Phases 13-19) | 5 | 23m | 4.6 min |

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

Last session: 2026-02-13
Stopped at: Completed 15-01-PLAN.md
Resume file: None

---

*Last updated: 2026-02-13 (Phase 15 Plan 01 complete)*
