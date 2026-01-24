# Research Summary: DonorCRM Journal Feature
## Fundraising Pipeline with Event Sourcing & Grid UI

**Project:** DonorCRM - Journal/Pipeline Feature (6-stage fundraising campaigns)
**Synthesized:** 2026-01-24
**Research Scope:** Stack, Features, Architecture, Pitfalls
**Overall Confidence:** HIGH

---

## Executive Summary

The Journal feature is a **hybrid event-sourced pipeline tracker** combining Django's ORM strength with React's grid interactivity. The recommended approach denormalizes current state for O(1) reads while maintaining append-only event logs for auditing. On the backend: Django 4.2 with TimeStampedModel, UUID keys, JSONField for flexible state, and explicit through models for many-to-many relationships. On the frontend: React 19 with TanStack Table for headless grid logic, Tailwind CSS for responsive layout, Radix UI for drawers/dialogs, and Recharts for analytics. This stack avoids pure event sourcing complexity while delivering complete audit trails and flexible workflows.

The critical implementation challenge is query optimization. Without deliberate denormalization and composite indexes, grid performance collapses at scale (100+ contacts). The second challenge is grid UX: cell re-renders must be memoized, optimistic updates required for responsiveness, and visual encoding essential to prevent "stale data lies" (checkmarks implying freshness when data is months old).

**Key Technologies:**
- **Backend:** Django 4.2 + DRF 3.14, event log + denormalized state pattern, append-only events with signal-driven updates
- **Frontend:** React 19 + TypeScript, TanStack Table (headless grid), React 19 useOptimistic for instant feedback, Tailwind CSS + Radix UI
- **Data Model:** Journal → JournalContact (through) → JournalStageEvent (append-only) + JournalContactStageState (denormalized current)
- **Decisions:** JournalDecisionCurrent (mutable) + JournalDecisionHistory (immutable) dual-table pattern

---

## Key Findings by Research Domain

### 1. Backend Technology Stack (STACK.md)

**Recommended Core:**
- **Django 4.2 + DRF 3.14** - Already in project, proven pattern
- **TimeStampedModel + UUID PK** - Use existing base class, provides created_at/updated_at auto-tracking
- **JSONField for pipeline state** - Native PostgreSQL JSONB, validates inline, no separate migrations for new state fields
- **DecimalField(max_digits=12, decimal_places=2)** - Money storage in cents (avoids float rounding)
- **Django Signals** - Append-only event creation via post_save hooks with transaction.on_commit()

**Query Optimization Essentials:**
- **select_related()** for ForeignKey upstream: Journal → Owner, Contact → Owner
- **prefetch_related()** for ManyToMany & reverse FK: Journal → Contacts → Events
- **Prefetch object** for custom filters: Only fetch recent 5 events per contact, not all
- **defer()/only()** for field-level optimization: Defer large TextField until detail view
- **Composite indexes** for common patterns: (contact, journal, created_at) for timeline queries

**DRF Serializer Pattern:**
- **No depth option** - Use explicit nested serializers (type-safe, maintainable)
- **Minimal nesting** - Events return only recent 5, not entire history
- **Read-only nested** - Journal detail includes contacts with events (but read-only)
- **SerializerMethodField** for computed fields: contact_count, owner_name

**Routing & Permissions:**
- **drf-nested-routers** for /journals/{id}/contacts/{id}/events/ URLs
- **Custom permission classes** for owner-scoped + admin-visible access
- **IsAuthenticated + IsOwnerOrAdminReadOnly** - Two-layer permission (view-level + object-level)

**Key Rationale:** Stack matches DonorCRM's existing patterns (Contact, Task, Donation models use same approach). Avoids custom frameworks. Leverages Django's ORM strength for event replay and aggregation queries.

---

### 2. Frontend Feature Patterns (FEATURES.md)

**Grid Core Pattern:**
- **TanStack Table v8** - Headless grid logic (already in project), robust sorting/filtering/pagination without UI opinions
- **Tailwind CSS Grid layout** - Sticky headers (top-0 z-50) + sticky contact column (left-0 z-40), overflow-auto for horizontal scroll
- **Pure CSS Grid over library** - For simplicity and performance, avoid Material-UI DataGrid overhead

**Drawer & Modal Interactions:**
- **Radix Sheet (Dialog-based)** - Event timeline drawer, right-slide, ScrollArea for long lists (already in project)
- **Radix HoverCard** - Quick event preview on hover (needs npm install @radix-ui/react-hover-card)
- **Dialog for "Add Contact"** - Existing Dialog component, reuse pattern

**State Management Pattern:**
- **React 19 useOptimistic** - Instant optimistic UI for stage moves and decision updates (new, built-in)
- **useReducer + Context** - Grid-level state (selectedCell, expandedDrawer, filters) - simple, performant
- **TanStack Query** - Server state (contacts, events), handles caching + background refetch
- **React 19 useActionState** - Form submissions with built-in loading state

**Charts & Reporting:**
- **Recharts** - Decision trends (bar), stage activity (area), pipeline breakdown (pie)
- **ResponsiveContainer** for auto-sizing, Tailwind Card components for consistency
- **Key metrics dashboard** - Total contacts, avg time per stage, conversion rate

**TypeScript Patterns:**
- **Discriminated unions** for event types - Switch on event.type for type-narrowing (moved_to_stage, note_added, decision_logged, call_logged)
- **Exhaustiveness checking** - Compiler ensures all event types handled
- **Type guards** - Helper functions for runtime type checks

**Accessibility Requirements:**
- **Grid ARIA attributes** - role="grid", role="row", role="gridcell", aria-rowcount/colcount
- **Keyboard navigation** - Arrow keys to move, Enter to open drawer, Home/End to jump
- **Single tab-stop pattern** - Tab to grid, arrow keys within (efficient for keyboard users)
- **Screen reader support** - aria-label describing cell content, event summaries

**Implementation Phases:**
1. **Phase 1 (MVP):** Static grid with TanStack Table + basic StageCell + EventTimelineDrawer
2. **Phase 2 (Interactions):** useGridState for selection, TanStack Query for data, optimistic updates
3. **Phase 3 (Forms):** Event creation form, "Add Contact" dialog, decision update
4. **Phase 4 (Analytics):** Recharts dashboard with decision/stage/revenue breakdowns
5. **Phase 5 (Polish):** ARIA attributes, keyboard nav, responsive breakpoints

**Key Rationale:** React 19 useOptimistic is native and designed for this use case (grid cells need instant feedback). Discriminated unions eliminate runtime type checking and provide IDE autocomplete. Tailwind sticky layout avoids component library bloat.

---

### 3. Architecture Patterns (ARCHITECTURE.md)

**Event Sourcing Strategy:**
- **NOT pure event replay** - Too slow for 100+ contacts with hundreds of events each
- **Append-only log + Denormalized state** (RECOMMENDED) - JournalStageEvent (immutable) + JournalContactStageState (current stage, timestamps)
- **Signal-driven updates** - On StageEvent create, signal updates current_stage in JournalContactStageState
- **Queries hit denormalized state for O(1) lookups** - Events remain append-only for audit trail

**Decision Tracking (Mutable State):**
- **Dual-table pattern:** JournalDecisionCurrent (one row, mutable) + JournalDecisionHistory (many rows, append-only)
- **UPDATE pattern:** Append old state to history first, then update current
- **NOT django-simple-history** - Too heavy for mostly-read models, explicit dual tables lighter weight

**Many-to-Many Relationship (Journal ↔ Contact):**
- **Explicit through model: JournalContact** - Required for timestamps (added_at, added_by), notes, is_active flag
- **unique_together = (journal, contact)** - Prevent duplicate membership
- **Indexes on (journal, is_active) and (contact, is_active)** - Common filters

**Django App Structure:**
- **Single `journals` app** - Journal, JournalContact, JournalStageEvent, JournalContactStageState, JournalDecisionCurrent/History all in one
- **High cohesion** - Bounded context, self-contained feature
- **services.py for business logic** - Keep models clean, logic testable (update_decision, log_stage_event, move_to_stage functions)

**API Design:**
- **Flat endpoints, not nested** - Simpler routing, query params for filtering
- **GET /journals/ — list all journals**
- **GET /journals/{id}/ — detail with contacts (but not deeply nested events)**
- **GET /journal-members/?journal={id} — contacts in journal**
- **GET /journal-events/?journal_contact={id} — stage events (paginated)**
- **Custom actions:** @action decorator for advance_stage, change_stage, move_to_stage

**Permission Inheritance:**
- **Queryset filtering at view-level** - Filter to owner's journals only (IsAuthenticated + role check)
- **Custom permission classes** - IsJournalOwnerOrReadOnly (object-level check), IsJournalMemberOwnerOrReadOnly (for nested resources)
- **Two-layer approach** - View-level filters + object-level checks = owner-scoped + admin visibility

**Report/Analytics Queries:**
- **ORM annotate/aggregate at query time** - Pipeline breakdown (count by stage), decision breakdown (count by status), revenue by cadence
- **NO application-level aggregation** - Database is optimized for this, avoids N+1
- **Prefetch + select_related** - Load related objects before aggregation to avoid additional queries

**Pipeline State Machine:**
- **Sequential but flexible** - Warn on skip/backward, don't block
- **Metadata tracking** - Store skipped_stages, is_revisited in event metadata for analytics
- **No rigid validation** - Allow staff judgment, log warnings for audit trail

**Key Rationale:** Denormalization prevents event replay performance cliff. Explicit through model enables membership metadata. Flat API simpler than nested routing. Queries optimized at ORM level. Single app follows DonorCRM pattern (contacts, tasks are single apps).

---

### 4. Critical Pitfalls & Mitigation (PITFALLS.md)

**CRITICAL PITFALLS (Phase-blocking):**

1. **N+1 Queries from Event Replay** → **Denormalize current_stage in JournalContactStageState.** Use prefetch_related with Prefetch objects to limit nested queries.

2. **Atomic Transaction Scope Bugs** → **Use @transaction.atomic for multi-model writes.** Always wrap decision update + history + event creation in single transaction. Use select_for_update() to lock rows.

3. **Event Replay Performance** → **Never compute current state by replaying events.** Always query denormalized JournalContactStageState. Snapshots add complexity with no benefit at this scale.

**MODERATE PITFALLS (Implementation-delaying):**

4. **React Grid Cell Re-render Cascade** → **Use React.memo + minimal prop passing.** Cell receives only contactId, stageCompleted, stageTimestamp (not entire rowData). Custom comparison in React.memo.

5. **Checkmark Lies (Stale Data)** → **Encode freshness in visual design.** Checkmark color changes based on age (green < 1 week, yellow < 1 month, orange < 3 months, red 3+ months). Include timestamp like "5d" or "2mo" next to checkmark.

6. **Sequential Pipeline Too Rigid/Loose** → **Warn, don't block.** Return warning metadata in API response (is_skip, stages_skipped), show toast warning in UI. Always allow save.

7. **Grid Virtualization Missing** → **Enable TanStack Virtual for >50 rows.** Render only visible rows + 10-row overscan. Saves 90% of DOM nodes for large grids.

8. **History Pagination Ignored** → **Paginate decision history at API level.** Default 25 records per page, provide "Load More" for older history. Use infinite scroll frontend pattern.

**MINOR PITFALLS (Annoyance-level):**

9. **Event Sourcing Signal Infinite Loops** → **Guard signals with created flag.** Use update() instead of save() to skip post_save signals. Test signal chains for circular dependencies.

10. **No Optimistic Updates** → **Implement React Query optimistic updates for all grid mutations.** Update cache immediately, rollback on error, refetch on settle.

11. **Hover Tooltips Spam API** → **Debounce hover with 300ms delay.** Cache tooltip data for 1 minute. Prevent 50+ API calls during mouse movement.

12. **CSV Export Without Streaming** → **Use StreamingHttpResponse + iterator(chunk_size=100).** Export 500+ rows without memory spike.

13. **Missing Composite Indexes** → **Add indexes for (contact, journal, -created_at) patterns** during initial migration. Verify with EXPLAIN ANALYZE before production.

**Phase-Specific Warnings:**
- **Phase 1 (Data Model):** Design queries correctly from start. Add indexes. Test signal chains.
- **Phase 2 (Decision Tracking):** Atomic transaction boundaries. History pagination API.
- **Phase 3 (Grid UI):** Memoization, virtualization, freshness encoding, optimistic updates.
- **Phase 4 (Reports):** Streaming export, ORM aggregation queries.

**Key Rationale:** Pitfall list is curated for THIS domain (pipeline + event sourcing + grid UI). Each pitfall has specific detection method and prevention code. Phase-specific warnings guide roadmap creation.

---

## Implications for Roadmap

### Suggested Phase Structure

**Phase 1: Data Model & Basic Grid (Week 1-2)**
- Create Journal, JournalContact, JournalStageEvent, JournalContactStageState, JournalDecisionCurrent/History models
- Add FK to Task.journal for context linking
- Create migrations with composite indexes (contact, journal, created_at)
- Implement JournalService for business logic (move_to_stage, update_decision)
- Create basic DRF serializers (list, detail variants)
- Implement JournalViewSet + permission classes
- Frontend: Static grid with TanStack Table, Tailwind sticky layout
- Frontend: Basic StageCell component showing event count
- **Key pitfall to avoid:** N+1 queries from event replay. Test with django-debug-toolbar.

**Phase 2: Decision Tracking & Events (Week 3-4)**
- Implement decision update endpoint with atomic transaction
- Create JournalEvent → Decision history append pattern
- Add decision_current serializer with history field (paginated)
- Implement change_stage custom action for stage transitions
- Frontend: Add useGridState for cell selection
- Frontend: Hook TanStack Query for contacts/events data fetch
- Frontend: EventTimelineDrawer (Radix Sheet) with recent 5 events
- **Key pitfall to avoid:** Atomic transaction scope bugs. Write tests for rollback scenarios.

**Phase 3: Grid Interactions & Optimistic Updates (Week 5-6)**
- Implement form for adding contacts to journal
- Add decision update dialog
- Frontend: React 19 useOptimistic for instant stage updates
- Frontend: Memoize cell components with React.memo
- Frontend: Add event count badges (color-coded by freshness)
- Frontend: Implement grid keyboard navigation (arrow keys, Enter)
- Frontend: Add ARIA attributes for accessibility
- Frontend: Responsive breakpoints (desktop grid, tablet 3 stages, mobile list)
- **Key pitfall to avoid:** Re-render cascade + missing memoization. Profile in React DevTools.

**Phase 4: Reporting & Analytics (Week 7-8)**
- Create report aggregation queries (pipeline breakdown, decision breakdown, revenue by cadence)
- Implement /journals/{id}/report/ action returning aggregated stats
- Frontend: Add ReportTab with Recharts charts (bar, area, pie)
- Frontend: Add key metrics dashboard (total contacts, avg time in stage, conversion rate)
- Implement CSV export with streaming response
- **Key pitfall to avoid:** Slow export for 500+ rows. Use StreamingHttpResponse + iterator.

**Phase 5: Polish & Performance (Week 9+)**
- Add grid virtualization (TanStack Virtual) for >100 contacts
- Fine-tune query performance (verify indexes, test with >200 contacts)
- Add dark mode Tailwind variants
- Mobile testing + Safari compatibility
- Implement hover debounce for tooltips
- Add analytics/logging for decision tracking
- **Key pitfall to avoid:** Stale data checkmark lies. Design freshness visual language.

### Dependencies Between Phases

- **Phase 1 → Phase 2:** Data model must be solid (Phase 1) before implementing decision logic (Phase 2)
- **Phase 2 → Phase 3:** Events must be working (Phase 2) before grid interactions (Phase 3)
- **Phase 3 → Phase 4:** Grid must be stable (Phase 3) before adding analytics (Phase 4)
- **Phase 4 → Phase 5:** Reports working (Phase 4) before performance optimization (Phase 5)

### Effort Estimation

| Phase | Focus | Est. Days | Risk Level |
|-------|-------|-----------|-----------|
| 1 | Models, API, basic grid | 5 | HIGH (queries must be right) |
| 2 | Decisions, events, forms | 4 | MEDIUM (transaction scoping) |
| 3 | Grid interactions, UI state | 4 | MEDIUM (React memoization) |
| 4 | Analytics, reports, export | 3 | LOW (ORM aggregation solid) |
| 5 | Polish, perf, accessibility | 3 | LOW (standard optimizations) |
| **Total** | | **19 days** | |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack Decisions** | HIGH | Based on DonorCRM's existing patterns, Django REST Framework official docs, proven libraries (TanStack Table already in project) |
| **Architecture Patterns** | HIGH | Event sourcing + denormalization hybrid well-documented, many-to-many through models standard Django practice |
| **Frontend Features** | HIGH | React 19 features (useOptimistic, useActionState) official, TanStack Table/Query already in project, Tailwind CSS mature |
| **Query Optimization** | HIGH | Django ORM performance patterns well-established, select_related/prefetch_related patterns proven |
| **Pitfalls** | MEDIUM-HIGH | General patterns researched from authoritative sources, some DonorCRM-specific validation needed during planning |
| **Permission Model** | MEDIUM | Role system (admin/staff/finance) assumed based on existing code; may need refinement during implementation |

**Gaps Requiring Validation:**
1. **Real-time updates** - Research doesn't address WebSocket + Query cache invalidation. Recommend Phase 2+ feature.
2. **Undo/Redo** - Not addressed. Current optimistic rollback sufficient for MVP; consider for Phase 5.
3. **Event editing** - Research covers creation. Editing requires similar optimistic pattern; recommend defer to Phase 3.
4. **Mobile performance** - Virtual scrolling tested on desktop; may need tuning for mobile browsers.

---

## Research Flags: Phase-Specific Needs

**Phase 1: Requires Research?** → **Yes (minor)** - Validate exact index strategy with DBA, confirm TimeStampedModel extends cleanly

**Phase 2: Requires Research?** → **No** - Atomic transaction patterns well-documented, dual-table decision pattern clear

**Phase 3: Requires Research?** → **Yes (minor)** - Fine-tune grid virtualization configuration for Tailwind CSS layout

**Phase 4: Requires Research?** → **No** - ORM aggregation patterns standard, streaming export documented

**Phase 5: Requires Research?** → **No** - Standard accessibility + performance optimization patterns

---

## Sources & Methodology

Research synthesized from:
- **STACK.md (898 lines):** Django 4.2 + DRF 3.14 patterns, TimeStampedModel, UUID PK, JSONField, Signals, Query optimization (select_related/prefetch_related), DRF ViewSets, nested routing, permissions
- **FEATURES.md (1,494 lines):** TanStack Table grid logic, Tailwind CSS fixed headers, Radix UI drawers/dialogs, React 19 Actions + useOptimistic, state management patterns, Recharts charting, TypeScript discriminated unions, accessibility patterns
- **ARCHITECTURE.md (1,555 lines):** Event sourcing vs denormalized state (Event Log + Computed State), Current + History tables for decisions, Through models (JournalContact), single app structure, flat API routing, permission inheritance, ORM aggregation queries, sequential pipeline with warnings
- **PITFALLS.md (1,161 lines):** N+1 queries, transaction scoping, event replay performance, grid re-render optimization, stale data UX, pipeline validation, virtualization, history pagination, signal loops, optimistic updates, tooltip spam, CSV export, missing indexes

**Confidence Basis:**
- Official documentation (Django, DRF, React, TanStack, Tailwind, Radix UI)
- Project codebase review (existing TimeStampedModel, Contact/Task/Donation patterns)
- Community patterns (Medium articles, GitHub repos, blog posts from Scout APM, TestDriven.io)
- Production-tested pitfall research (performance benchmarks, real-world case studies)

---

## Recommendation Summary

**Build the Journal feature as a hybrid event-sourced system:** append-only event logs (audit trail) + denormalized current state (performance). Use Django's ORM strength for queries, don't fight it with pure event replay. Implement React 19's native optimistic update pattern for instant grid feedback. Encode data freshness visually (color + timestamp) to prevent "checkmark lies." Optimize queries from Phase 1 (indexes, prefetch patterns) rather than bolting on later.

The roadmap is 5 phases over ~4 weeks with manageable scope: data model → decisions → grid interactions → analytics → polish. Highest risk is Phase 1 (query design) and Phase 3 (React memoization). Leverage existing project libraries (TanStack Table/Query, Radix UI, TimeStampedModel) to move faster.

**READY FOR REQUIREMENTS DEFINITION.**
