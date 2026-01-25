# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** A missionary can look at their journal and instantly know what's next for each donor and what they've completed so far.

**Current focus:** Phase 5 complete - Ready for Phase 6 (Polish & Data Integrity)

## Current Position

Phase: 6 of 6 (Reporting & Integration) - COMPLETE
Plan: 3 of 3 in current phase - COMPLETE
Status: Phase complete
Last activity: 2026-01-25 — Completed 06-03-PLAN.md (Contact Journals API)

Progress: [████████████] 70% (21 of 30 total plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 21
- Average duration: 2.8 minutes
- Total execution time: 1.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 Foundation & Data Model | 2 | 10 min | 5 min |
| 02 Contact Membership & Search | 2 | 7 min | 3.5 min |
| 03 Decision Tracking | 3 | 10 min | 3.3 min |
| 04 Grid UI Core | 5 | 9 min | 1.8 min |
| 05 Grid Interactions & Decision UI | 6 | 20 min | 3.3 min |
| 06 Reporting & Integration | 3 | 15 min | 5 min |

**Recent Trend:**
- Last 5 plans: [2m, 5m, 4m, 5m, 6m]
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
- Sticky CSS over virtualization for initial implementation (04-03: dataset size doesn't require virtualization complexity)
- Z-index hierarchy: z-10 headers, z-20 columns, z-30 intersection (04-03: prevents overlap during bi-directional scroll)
- 300ms tooltip delay to prevent interference with clicks (04-03: delayDuration on Tooltip component)
- Horizontal scroll via min-width constraints (04-05: table min-width 900px, fixed column widths force scrolling)
- stage_events computed in serializer (04-05: JournalContactSerializer.get_stage_events aggregates events per stage)
- Toaster position bottom-right for non-intrusive notifications (05-01: global toast access via toast() API)
- Full shadcn/ui Select component with scroll buttons for long option lists (05-01: handles long dropdown lists gracefully)
- NextStepSerializer handles completed_at timestamp in update() method (05-02: automatic timestamp when marking complete/uncomplete)
- Generic views over ViewSet for NextStep API (05-02: consistency with existing decision and journal patterns)
- Optimistic updates with onMutate/onError/onSettled pattern (05-03: addresses pitfall, provides instant UI feedback with rollback)
- Memoized stats in JournalHeader (05-03: useMemo prevents cascade re-renders when cells update)
- DecisionSummary filter excludes declined status from totals (05-03: only pending/active/paused count toward progress)
- getHighestStageWithEvents helper determines current stage for transition warnings (05-04: scans stages from next_steps down to contact)
- Lazy loading NextSteps only when popover opens (05-04: enabled: isOpen for performance)
- Stage warnings via toast.warning - non-blocking per JRN-05 (05-04: always proceed, warning only)
- Direct badge variant mapping for status colors (05-05: success/warning/secondary/destructive map to active/pending/paused/declined)
- DecisionDialog and DecisionCell memoized with React.memo (05-05: prevents cascade re-renders)
- JournalHeader separate from back button for clean layout (05-06: back button -> header -> grid)
- journalId prop threading for decision mutations (05-06: passed through grid to DecisionCell)
- ViewSet with @action decorators for analytics endpoints (06-01: DRF best practice for grouping related endpoints)
- TruncMonth aggregation for monthly trends (06-01: efficient database-level grouping)
- Subquery for current stage determination (06-01: avoids N+1 queries)
- Pivot pattern with defaultdict for stage-activity (06-01: frontend-ready format)
- owner__email instead of owner__username (06-01: User model uses email as identifier)
- Optional journal FK on Task model (06-02: null=True, blank=True enables journal-specific tasks without requiring all tasks be journal-linked)
- CASCADE delete for journal tasks (06-02: when journal deleted, its tasks deleted - appropriate for journal-specific context)
- Manual chart component creation (06-02: project lacks components.json, created chart.tsx following existing shadcn component pattern)
- Prefetch with to_attr pattern (06-03: enables serializer access to prefetched data with fallback)
- Separate ListAPIView for contact endpoints (06-03: consistency with ContactDonationsView, ContactPledgesView, ContactTasksView patterns)
- Stage computed from most recent event (06-03: matches grid UI behavior from 04-05)

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 Research Flags (from SUMMARY.md):**
- Validate exact index strategy with production data patterns (composite indexes for contact, journal, created_at)
- Confirm TimeStampedModel extends cleanly for all new models

**Critical Pitfalls to Avoid:**
- Phase 1: N+1 queries from event replay (must denormalize current_stage in JournalContactStageState)
- Phase 2: Atomic transaction scope bugs (wrap decision update + history + event creation in single transaction)
- Phase 5: Optimistic update rollback on error (use React Query mutation onError callbacks) - ADDRESSED

## Session Continuity

Last session: 2026-01-25 (plan execution)
Stopped at: Completed 06-03-PLAN.md (Contact Journals API)
Resume file: None

**Next steps:** Phase 6 complete - all 3 plans executed. Project 70% complete (21/30 plans).
