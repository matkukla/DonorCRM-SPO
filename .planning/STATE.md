# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** A missionary can look at their journal and instantly know what's next for each donor and what they've completed so far.

**Current focus:** Phase 4 - Grid UI Core

## Current Position

Phase: 4 of 6 (Grid UI Core)
Plan: 4 of 5 in current phase
Status: In progress
Last activity: 2026-01-24 — Completed 04-04-PLAN.md (Event Timeline Drawer)

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 2.8 minutes
- Total execution time: 0.43 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 Foundation & Data Model | 2 | 10 min | 5 min |
| 02 Contact Membership & Search | 2 | 7 min | 3.5 min |
| 03 Decision Tracking | 3 | 10 min | 3.3 min |
| 04 Grid UI Core | 2 | 3 min | 1.5 min |

**Recent Trend:**
- Last 5 plans: [5m, 7m, 5m, 2m, 1m]
- Trend: Excellent velocity - averaging 2.8 minutes per plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Django/DRF over Node/Prisma - Follow existing codebase patterns
- Link journal tasks to existing Task model - Avoid duplicate task systems, reuse existing UI
- Owner + admin visibility for journals - Supports future cross-missionary analytics without full admin UI
- Fixed 6-stage pipeline - Matches missionary fundraising workflow, avoid over-engineering
- DecimalField for money storage - Changed from integer cents to DecimalField (01-01: follows existing pledges/donations pattern)
- Archive pattern for journals - Soft delete with is_archived + archived_at (01-01: preserves historical data)
- Append-only event log - JournalStageEvent immutable (01-01: complete audit trail)
- Soft delete via DELETE verb - DELETE /journals/{id}/ calls archive() not hard delete (01-02: preserves audit trail, consistent with UX)
- Signal-based event logging - Import Event model inside handlers to avoid circular imports (01-02: follows pledges pattern)
- Serializer-level ownership validation - For multi-entity relationships without direct owner (02-01: JournalContact validates both journal.owner and contact.owner)
- Duplicate membership handling - Atomic transaction + IntegrityError catch returns 400 instead of 500 (02-01: user-friendly error handling)
- Read-only denormalized fields - contact_name/email/status in serializer avoid N+1 queries (02-01: efficient list display)
- UUID string comparison in tests - DRF returns UUID objects, convert to strings for assertions (02-02: str(response.data['field']))
- Flexible error format validation - Accept both 'detail' and 'non_field_errors' for duplicate validation (02-02: DRF may catch at serializer or database level)
- DecimalField for decision amounts - Follows existing pledges/donations pattern (03-01: consistent with codebase)
- Quarterly/Annual cadence multipliers - Use Decimal division with round(result, 2) for monthly_equivalent (03-01: Decimal('1')/Decimal('3') for quarterly, Decimal('1')/Decimal('12') for annual)
- One-time decisions excluded from monthly - monthly_equivalent returns Decimal('0') for one_time cadence (03-01: one-time gifts not counted in recurring calculations)
- Serializer-level ownership validation for journal_contact - Validate journal ownership in DecisionSerializer (03-02: multi-entity relationships without direct owner field)
- History tracking in serializer.update() - Serializer has request.user context for changed_by field (03-02: model save() doesn't have user context)
- Decimal to string conversion in history - JSONField requires JSON primitives, convert Decimal to string for storage (03-02: preserves precision while being JSON serializable)
- Test pagination awareness - Decision list uses default StandardPagination (03-03: tests must use response.data['count'] and response.data['results'])
- Separate journal_contacts for tests - Avoid unique constraint conflicts in setUp (03-03: create new contacts/journal_contacts in tests needing fresh decisions)
- Decimal iteration for history tests - Ensure each update differs from previous (03-03: use range(1, 31) to avoid no-op updates)
- Simple date math in getFreshnessColor - Use vanilla JS instead of date-fns in types file (04-01: keeps type file lightweight, no runtime dependencies)
- Orange Badge variant for 1-3 month freshness - Positioned between warning yellow and destructive red (04-01: visual distinction for "needs attention soon")
- Types match Django field names exactly - JournalMember, PipelineStage, etc use exact Django values (04-01: zero impedance mismatch between frontend/backend)
- useInfiniteQuery for event timeline with page number parsing from DRF next URL (04-02: parse page param from pagination.next for getNextPageParam)
- Query keys follow [journals, ...] pattern for cache invalidation (04-02: hierarchical cache management with resource-based keys)
- Sheet drawer opens from right with w-full sm:w-[400px] responsive width (04-04: mobile-first design with max-width on desktop)
- 5 events per page with Load More pagination (04-04: explicit button over auto-load for user control)
- Timeline visual with dots and vertical line connector (04-04: chronological flow pattern for event history)
- Relative time with absolute on hover (04-04: formatDistanceToNow for quick scanning, tooltip for precise timestamp)

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 Research Flags (from SUMMARY.md):**
- Validate exact index strategy with production data patterns (composite indexes for contact, journal, created_at)
- Confirm TimeStampedModel extends cleanly for all new models

**Phase 3 Research Flags:**
- Fine-tune grid virtualization configuration for Tailwind CSS layout

**Critical Pitfalls to Avoid:**
- Phase 1: N+1 queries from event replay (must denormalize current_stage in JournalContactStageState)
- Phase 2: Atomic transaction scope bugs (wrap decision update + history + event creation in single transaction)
- Phase 4: React grid cell re-render cascade (use React.memo + minimal prop passing)

## Session Continuity

Last session: 2026-01-24 (plan execution)
Stopped at: Completed 04-04-PLAN.md (Event Timeline Drawer)
Resume file: None

**Next steps:** Continue Phase 4 - Plans 04-03 and 04-05 for grid UI components
