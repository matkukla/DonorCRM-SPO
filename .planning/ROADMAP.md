# Roadmap: DonorCRM Journal Feature

## Overview

The Journal feature builds a fundraising campaign pipeline tracker in six phases, starting with foundational data models and APIs, then layering on decision tracking, grid UI, reporting, and integrations. Each phase delivers testable, user-facing value. The journey moves from "backend works" to "grid displays data" to "user can interact" to "user can analyze" to "system integrates with existing features."

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Data Model** - Core models, API endpoints, event logging
- [x] **Phase 2: Contact Membership & Search** - Add/remove contacts, filtering
- [x] **Phase 3: Decision Tracking** - Current state + history with dual-table pattern
- [x] **Phase 4: Grid UI Core** - Static grid, stage cells, event timeline drawer
- [ ] **Phase 5: Grid Interactions & Decision UI** - Optimistic updates, decision dialogs, next steps
- [ ] **Phase 6: Reporting & Integration** - Analytics charts, contact detail integration, task linking

## Phase Details

### Phase 1: Foundation & Data Model
**Goal**: Backend foundation exists with all core models, migrations, API endpoints, and permission layer. User can create/edit/archive journals via API.

**Depends on**: Nothing (first phase)

**Requirements**: JRN-01, JRN-04, JRN-18

**Success Criteria** (what must be TRUE):
1. User can create a journal with name, goal amount, and deadline via POST /api/v1/journals/
2. User can edit journal fields via PATCH /api/v1/journals/{id}/
3. User can archive a journal (soft delete) via DELETE /api/v1/journals/{id}/
4. System logs stage events when created (append-only with timestamp)
5. User sees only their own journals, admins see all journals (permission enforcement working)

**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — App scaffolding, models, enums, and migrations
- [x] 01-02-PLAN.md — Serializers, views, URLs, signals, and API integration

---

### Phase 2: Contact Membership & Search
**Goal**: User can add/remove contacts to journals and search/filter within a journal. Many-to-many relationship works with contact picker.

**Depends on**: Phase 1

**Requirements**: JRN-02, JRN-03

**Success Criteria** (what must be TRUE):
1. User can add multiple contacts to a journal via POST /api/v1/journal-members/
2. User can remove contacts from a journal via DELETE /api/v1/journal-members/{id}/
3. Contact can belong to multiple journals simultaneously (no uniqueness violation errors)
4. User can search contacts within a journal by name/email via query params
5. User can filter contacts by stage or decision status

**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Serializer, views, and URL routing for journal membership API
- [x] 02-02-PLAN.md — Integration tests covering all success criteria

---

### Phase 3: Decision Tracking
**Goal**: System tracks current decision state and full history using dual-table pattern. User can update decisions and see history.

**Depends on**: Phase 2

**Requirements**: JRN-07, JRN-08, JRN-09

**Success Criteria** (what must be TRUE):
1. User can record a decision with amount, cadence (one-time/monthly/quarterly/annual), and status
2. User can update an existing decision, and system appends old state to history table before updating current
3. System calculates monthly equivalent for all cadences correctly (quarterly → amount/3, annual → amount/12)
4. User can retrieve decision history for a contact in a journal, paginated (default 25 records)
5. Each contact has at most one current decision per journal (unique constraint enforced)

**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Decision and DecisionHistory models with enums and migration
- [x] 03-02-PLAN.md — Serializers, views, and URL routing for decision API
- [x] 03-03-PLAN.md — Integration tests for all success criteria

---

### Phase 4: Grid UI Core
**Goal**: User sees a functional grid with contacts as rows, stages as columns, and can open event timeline drawer. Grid displays data from API.

**Depends on**: Phase 3

**Requirements**: JRN-10, JRN-11, JRN-12

**Success Criteria** (what must be TRUE):
1. User sees grid layout with sticky column headers (stages) and sticky first column (contact names)
2. Stage cells display checkmarks when stage has logged events
3. Checkmark color indicates event freshness (green: <1 week, yellow: <1 month, orange: <3 months, red: 3+ months)
4. User can hover over stage cell to see tooltip with most recent event summary
5. User can click stage cell to open right-side drawer showing chronological event timeline
6. Timeline drawer loads recent 5 events by default with "Load More" option
7. Grid supports horizontal scroll for all 6 stage columns

**Plans**: 5 plans

Plans:
- [x] 04-01-PLAN.md — Setup dependencies (Tooltip, date-fns, Badge variant, TypeScript types)
- [x] 04-02-PLAN.md — Journal API client and React Query hooks
- [x] 04-03-PLAN.md — JournalGrid component with sticky headers and StageCell
- [x] 04-04-PLAN.md — EventTimelineDrawer with infinite scroll pagination
- [x] 04-05-PLAN.md — JournalDetail page integration and visual verification

---

### Phase 5: Grid Interactions & Decision UI
**Goal**: User can interact with the grid: update decisions, create events, manage next steps. Optimistic updates provide instant feedback.

**Depends on**: Phase 4

**Requirements**: JRN-05, JRN-06, JRN-13, JRN-14

**Success Criteria** (what must be TRUE):
1. User can click decision column cell to open dialog and update amount/cadence/status
2. Decision updates apply optimistically (UI updates immediately, rolls back on error)
3. User can move contact to different stage, and system shows warning toast if skipping/reversing stages (but allows save)
4. User can create, edit, and mark complete Next Steps checklist items per contact
5. Journal header displays name, goal amount, progress bar, total decisions made, and total pledged amount
6. Header progress calculation updates in real-time as decisions change
7. Grid cells re-render efficiently (memoized, no cascade re-renders when interacting with single cell)

**Plans**: 6 plans

Plans:
- [x] 05-01-PLAN.md — UI dependencies (Sonner, Select, Progress, Checkbox components)
- [x] 05-02-PLAN.md — NextStep backend model, serializer, views, and tests
- [ ] 05-03-PLAN.md — Decision API functions, optimistic mutation hooks, JournalHeader
- [ ] 05-04-PLAN.md — Stage movement warnings and NextSteps frontend
- [ ] 05-05-PLAN.md — DecisionDialog and DecisionCell components
- [ ] 05-06-PLAN.md — Page integration with human verification

---

### Phase 6: Reporting & Integration
**Goal**: User can view analytics reports, see journal membership from contact detail page, and create journal-specific tasks.

**Depends on**: Phase 5

**Requirements**: JRN-15, JRN-16, JRN-17, JRN-19

**Success Criteria** (what must be TRUE):
1. User can open Report tab and see decision trends chart (bar: decisions over time)
2. User can view stage activity chart (area: events by stage) and pipeline breakdown (pie: contacts by stage)
3. User can view next steps queue showing upcoming actions across all contacts
4. Contact detail page has new "Journals" tab showing all journals this contact belongs to
5. Journals tab displays current stage and decision for each journal the contact is in
6. User can create a task linked to a journal (Task.journal_id populated)
7. Journal-linked tasks appear in journal context and in standard task views
8. Admin can access analytics endpoints for cross-missionary aggregation (total journals, decision totals, stage averages)
9. Report queries execute without N+1 problems (verified with django-debug-toolbar)

**Plans**: TBD

Plans:
- [ ] TBD

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Data Model | 2/2 | Complete | 2026-01-24 |
| 2. Contact Membership & Search | 2/2 | Complete | 2026-01-24 |
| 3. Decision Tracking | 3/3 | Complete | 2026-01-24 |
| 4. Grid UI Core | 5/5 | Complete | 2026-01-25 |
| 5. Grid Interactions & Decision UI | 2/6 | In progress | - |
| 6. Reporting & Integration | 0/TBD | Not started | - |
