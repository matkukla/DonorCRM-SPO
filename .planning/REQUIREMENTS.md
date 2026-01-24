# Requirements: DonorCRM Journal Feature

## Overview

This document catalogs all requirements for the Journal feature (fundraising campaign pipeline tracker). Requirements are versioned as v1 (current milestone) and v2 (future work).

## v1 Requirements

### Core Journal Management

**JRN-01: Journal CRUD Operations**
- User can create, edit, and archive journals
- Each journal has a name, goal amount (in cents), and optional deadline
- Owner-scoped: user sees their journals, admins see all

**JRN-02: Contact Membership**
- User can add/remove contacts to journals
- Many-to-many: contacts can be in multiple journals simultaneously
- Contacts can be added via "Add Contacts" picker dialog

**JRN-03: Search and Filter Contacts**
- User can search contacts within a journal grid
- User can filter contacts by stage, decision status, or next steps

### Pipeline Tracking

**JRN-04: Stage Event Logging**
- System logs events across 6 stages: Contact → Meet → Close → Decision → Thank → Next Steps
- Each stage has typed events (e.g., Contact stage: call logged, email sent; Close stage: ask made, follow-up scheduled)
- Events are append-only with timestamps and metadata

**JRN-05: Sequential Pipeline Flexibility**
- User can skip stages or revisit previous stages
- System shows subtle warnings for non-sequential movement (no hard blocks)
- Movement patterns logged for analytics

**JRN-06: Next Steps Checklist**
- User can create, edit, and mark complete checklist items per contact per journal
- Next Steps are independent items (not single boolean)
- Visible in journal grid and contact detail

### Decision Tracking

**JRN-07: Decision Current State**
- System tracks current decision state: amount (in cents), cadence (one-time/monthly/quarterly/annual), status
- One current decision per contact per journal (unique constraint)
- Decisions mutable: user can update amount, cadence, or status

**JRN-08: Decision History**
- System maintains full history of decision changes
- Each update appends to history table before updating current state
- History includes timestamp, changed fields, and old values

**JRN-09: Decision Cadence Support**
- User can record one-time, monthly, quarterly, or annual pledge cadences
- System normalizes to monthly equivalent for aggregation
- Report calculations use monthly equivalent for comparisons

### User Interface - Grid View

**JRN-10: Journal Detail Grid**
- User sees grid with contacts as rows, stages as columns
- Grid has sticky headers (stages) and sticky first column (contact names)
- Grid supports horizontal scroll for all 6+ columns

**JRN-11: Stage Cell Indicators**
- Each stage cell shows checkmark if stage has events
- User can hover cell to see tooltip with recent event summary
- Checkmark color indicates freshness (green: <1 week, yellow: <1 month, orange: <3 months, red: 3+ months)

**JRN-12: Event Timeline Drawer**
- User can click stage cell to open right-side drawer
- Drawer shows chronological event timeline for that contact in that stage
- Events paginated (recent 5 default, load more option)

**JRN-13: Decision Column Display**
- Decision column shows card with amount, cadence, and status
- User can click to open decision update dialog
- Card uses color coding for status (pending/active/paused/declined)

**JRN-14: Journal Header Summary**
- Header shows journal name, goal amount, current progress bar
- Shows total decisions made (count) and total amount pledged
- Shows percentage toward goal

### User Interface - Reporting

**JRN-15: Report Tab Analytics**
- User can view Report tab showing:
  - Decision trends chart (bar: decisions over time)
  - Stage activity chart (area: events by stage)
  - Pipeline breakdown (pie: contacts by stage)
  - Next steps queue (list: upcoming actions)

### Integration

**JRN-16: Contact Detail Integration**
- Contact detail page has new "Journals" tab
- Tab shows all journals this contact belongs to
- Shows current stage and decision for each journal

**JRN-17: Task System Integration**
- Existing Task model extended with optional journal_id foreign key
- User can create journal-specific tasks from journal grid
- Tasks visible in journal context and standard task views

### Access Control & Analytics Foundation

**JRN-18: Owner and Admin Visibility**
- Users see only their journals
- Admins see all journals across all users
- Permission class follows existing IsContactOwnerOrReadAccess pattern

**JRN-19: Admin Analytics Endpoints**
- API provides endpoints for cross-missionary aggregation:
  - Total journals by user
  - Decision totals by user
  - Stage completion averages
- Admin UI deferred to v2 (endpoints only)

## v2 Requirements (Future)

The following are explicitly out of scope for v1 but planned for future releases:

**JRN-V2-01: Admin Analytics Dashboard**
- Admin UI showing cross-missionary metrics
- Comparative reports, leaderboards, trend analysis

**JRN-V2-02: Real-Time Collaboration**
- Multi-user concurrent editing
- WebSocket-based live updates

**JRN-V2-03: Communication Integration**
- Email/SMS sending from stage actions
- Template-based communication tracking

**JRN-V2-04: Mobile Native App**
- iOS/Android apps (currently web responsive only)

**JRN-V2-05: Bulk Journal Operations**
- Copy journal with contacts
- Bulk archive/activate journals

**JRN-V2-06: Custom Stage Definitions**
- User-defined pipeline stages (currently fixed 6-stage)

**JRN-V2-07: AI Suggestions**
- ML-driven next action recommendations

## Traceability

Requirement-to-Phase mapping (updated during roadmap creation):

| Requirement | Phase | Status |
|-------------|-------|--------|
| JRN-01 | Phase 1 | Complete |
| JRN-02 | Phase 2 | Pending |
| JRN-03 | Phase 2 | Pending |
| JRN-04 | Phase 1 | Complete |
| JRN-05 | Phase 5 | Pending |
| JRN-06 | Phase 5 | Pending |
| JRN-07 | Phase 3 | Pending |
| JRN-08 | Phase 3 | Pending |
| JRN-09 | Phase 3 | Pending |
| JRN-10 | Phase 4 | Pending |
| JRN-11 | Phase 4 | Pending |
| JRN-12 | Phase 4 | Pending |
| JRN-13 | Phase 5 | Pending |
| JRN-14 | Phase 5 | Pending |
| JRN-15 | Phase 6 | Pending |
| JRN-16 | Phase 6 | Pending |
| JRN-17 | Phase 6 | Pending |
| JRN-18 | Phase 1 | Complete |
| JRN-19 | Phase 6 | Pending |

**Coverage:** 19/19 requirements mapped (100%)

---

*Requirements defined: 2026-01-24*
*Last updated: 2026-01-24*
