# Roadmap: DonorCRM

## Milestones

- ✅ **v1.0 Journal Feature** -- Phases 1-6 (shipped 2026-01-29)
- ✅ **v1.1 CSV Import** -- Phases 7-12 (shipped 2026-02-04)
- ✅ **v1.2 Admin Analytics Dashboard** -- Phases 13-19 (shipped 2026-02-16)
- ✅ **v1.3 Smartsheet Import, Filters & Polish** -- Phases 20-26 (shipped 2026-02-19)
- ✅ **v2.0 Import Revamp, Prayer Intentions & Dashboard Polish** -- Phases 27-36 (shipped 2026-02-25)
- ✅ **v2.1 Security Hardening** -- Phase 37 (shipped 2026-02-25)
- [ ] **v2.2 UI Polish, Journal Report & Supervisor Role** -- Phases 38-42 (in progress)

## Phases

<details>
<summary>v1.0 Journal Feature (Phases 1-6) -- SHIPPED 2026-01-29</summary>

See milestones/v1.0-ROADMAP.md for complete phase details.

**Key Features:**
- Journal CRUD with owner-scoped visibility
- 6-stage pipeline with decision tracking
- Interactive grid UI with analytics charts
- Contact detail integration and task system

**Scope:** 19 requirements, 6 phases, 24 plans

</details>

<details>
<summary>v1.1 CSV Import (Phases 7-12) -- SHIPPED 2026-02-04</summary>

See milestones/v1.1-ROADMAP.md for complete phase details.

**Key Features:**
- Import Center UI for 4 CSV types
- Fund model, external IDs, import audit trail

**Scope:** 19 requirements, 6 phases, 15 plans

</details>

<details>
<summary>v1.2 Admin Analytics Dashboard (Phases 13-19) -- SHIPPED 2026-02-16</summary>

See milestones/v1.2-ROADMAP.md for complete phase details.

**Key Features:**
- Dashboard Overview with summary cards, trend charts, conversion funnel
- Stalled Contacts monitoring, User Detail pages
- Interactive drill-down, heatmap, time period comparison

**Scope:** 26 requirements, 7 phases, 18 plans

</details>

<details>
<summary>v1.3 Smartsheet Import, Filters & Polish (Phases 20-26) -- SHIPPED 2026-02-19</summary>

See milestones/v1.3-ROADMAP.md for complete phase details.

**Key Features:**
- Security fixes (permission bypass, N+1 queries, file size limits, route guards)
- Dark mode color audit, Error Boundary, CSV sanitization
- Reusable filter system with URL persistence, presets, badges, filtered CSV export
- Per-page filters on all 5 list pages with admin owner dropdowns
- Smartsheet MPD import (file upload, format detection, name matching, financial snapshots)
- MPD data on admin dashboard and missionary personal views

**Scope:** 35 requirements, 7 phases, 20 plans, 37 tasks

</details>

<details>
<summary>v2.0 Import Revamp, Prayer Intentions & Dashboard Polish (Phases 27-36) -- SHIPPED 2026-02-25</summary>

See milestones/v2.0-ROADMAP.md for complete phase details.

**Key Features:**
- Gift/RecurringGift models replacing Donation/Pledge (full data migration)
- Raiser's Edge CSV import pipeline (4 types: Constituent, Solicitor, Gift, Recurring Gift)
- Generic CSV import (contacts, donations) with configurable matching
- Solicitor model with auto-linking and credit splitting
- Prayer Intentions with Focus Mode, Today's Focus, contact integration
- Draggable dashboard tiles (dnd-kit)
- Full-stack audit: 52 issues fixed (security, performance, code quality, UI/UX)

**Scope:** 46 requirements, 10 phases, 27 plans

</details>

<details>
<summary>v2.1 Security Hardening (Phase 37) -- SHIPPED 2026-02-25</summary>

See milestones/v2.1-ROADMAP.md for complete phase details.

**Key Features:**
- Auth rate limiting and refresh token rotation fix
- Content-Security-Policy, Referrer-Policy, Permissions-Policy headers
- API docs authentication gate in production
- Python and JS dependency CVE patches
- Comprehensive SECURITY-REPORT.md

**Scope:** 1 phase, 3 plans, 6 tasks

</details>

### v2.2 UI Polish, Journal Report & Supervisor Role (In Progress)

**Milestone Goal:** Refine the UI across all major pages, rebuild the journal report component, add Begin Prayer flow, and introduce the Mission Supervisor role with scoped visibility.

- [x] **Phase 38: UI Polish & List Page Cleanup** - Center dialogs, rename labels, and clean up list page columns across contacts, gifts, pledges, and analytics (completed 2026-02-27)
- [ ] **Phase 39: Dashboard Modifications** - Remove stale text and tiles, tighten spacing, add chart toggle, and enable cross-section tile dragging
- [ ] **Phase 40: Journal Report & Grid Behavior** - Rebuild journal report with new metrics/charts and make grid stage checkboxes directly clickable
- [ ] **Phase 41: Begin Prayer** - Add a dedicated prayer session entry point that launches expanded Focus Mode
- [ ] **Phase 42: Mission Supervisor Role** - New role with scoped visibility, assignment management, and missionary dashboard selector

## Phase Details

### Phase 38: UI Polish & List Page Cleanup
**Goal**: Users see a cleaner, more consistent UI across all list pages and modal dialogs
**Depends on**: Nothing (first v2.2 phase)
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, ANLY-01, ANLY-02
**Success Criteria** (what must be TRUE):
  1. Every modal dialog in the application opens centered on screen (not offset or side-sliding)
  2. The contacts page displays "Potential Donor" everywhere that previously said "Prospect"
  3. The gifts list page shows a Type column (Credit Card / Direct Deposit / Check) and no longer shows Fund or Description columns
  4. The pledges list page no longer shows a Fund column
  5. The analytics dashboard no longer shows the Review Queue section or the activity heat map
**Plans**: 3 plans

Plans:
- [x] 38-01-PLAN.md — Gift payment_type field + list/detail column updates (UI-03, UI-04, UI-05)
- [x] 38-02-PLAN.md — Sheet-to-Dialog conversion + Prospect rename (UI-01, UI-02)
- [x] 38-03-PLAN.md — Analytics cleanup: Review Queue + Heatmap removal (ANLY-01, ANLY-02)

### Phase 39: Dashboard Modifications
**Goal**: The missionary dashboard is visually tighter and more flexible with cleaner cards and full drag-and-drop control
**Depends on**: Nothing (independent of Phase 38)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. User can toggle the Donations chart between bar chart and line graph views
  2. User can drag any dashboard tile to any position across all sections (cross-section dragging works)
  3. Dashboard tiles have visually reduced gaps between them compared to current layout
  4. The Giving summary card no longer displays "2026 calendar year" text, and the Monthly Gifts card no longer displays "Updated today" text
  5. The "Recent Journal Activity" tile is no longer visible on the dashboard
**Plans**: 2 plans

Plans:
- [ ] 39-01-PLAN.md — Backend layout persistence + chart toggle + text/tile removals (DASH-01, DASH-04, DASH-05, DASH-06)
- [ ] 39-02-PLAN.md — Flat grid restructure + spacing + backend persistence integration (DASH-02, DASH-03)

### Phase 40: Journal Report & Grid Behavior
**Goal**: Users get a rebuilt, actionable journal report and can advance contacts through pipeline stages with a single click
**Depends on**: Nothing (independent of Phases 38-39)
**Requirements**: JRNL-01, JRNL-02, JRNL-03, JRNL-04, JRNL-05, JRNL-06, JRNL-07, JRNL-08
**Success Criteria** (what must be TRUE):
  1. Journal report tab displays 4 metric cards (Total Contacts, With Decisions, Confirmed $, Pending), a goal progress bar, a Contacts by Stage bar chart, and a Decision Status donut chart
  2. Journal report shows conditional alert sections for stalled contacts and open next steps when applicable
  3. Pipeline Breakdown chart is no longer visible in journal reports
  4. User can click a stage checkbox in the journal grid and it immediately checks (auto-creates a stage event) without opening a dialog
  5. A Decision column exists between Close and Thank in the journal grid, and clicking it opens a decision creation flow (not a checkbox)
**Plans**: TBD

Plans:
- [ ] 40-01: TBD
- [ ] 40-02: TBD
- [ ] 40-03: TBD

### Phase 41: Begin Prayer
**Goal**: Users can launch a dedicated prayer session directly from the Prayer Request page
**Depends on**: Nothing (independent of all other phases)
**Requirements**: PRAY-01
**Success Criteria** (what must be TRUE):
  1. The Prayer Request page displays a prominent "Begin Prayer" button
  2. Clicking "Begin Prayer" launches the expanded Focus Mode with today's prayer intentions loaded
**Plans**: TBD

Plans:
- [ ] 41-01: TBD

### Phase 42: Mission Supervisor Role
**Goal**: Organization leadership can assign supervisors to missionaries, and supervisors see only their assigned missionaries' data across the entire application
**Depends on**: Phases 38-41 (execute last to avoid merge conflicts with Q helper refactor across 40+ views)
**Requirements**: SUPV-01, SUPV-02, SUPV-03, SUPV-04
**Success Criteria** (what must be TRUE):
  1. Mission Supervisor exists as a selectable role in the system, and admin can assign it to a user
  2. Admin can assign specific missionaries to a supervisor via the user management UI
  3. A supervisor sees only their assigned missionaries' data on all pages (contacts, gifts, recurring gifts, tasks, journals, prayers, analytics)
  4. Admin and supervisor can select a missionary from a dropdown and view that missionary's personal dashboard
**Plans**: TBD

Plans:
- [ ] 42-01: TBD
- [ ] 42-02: TBD
- [ ] 42-03: TBD
- [ ] 42-04: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 38 -> 39 -> 40 -> 41 -> 42

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1.0 | 24/24 | Complete | 2026-01-29 |
| 7-12 | v1.1 | 15/15 | Complete | 2026-02-04 |
| 13-19 | v1.2 | 18/18 | Complete | 2026-02-16 |
| 20-26 | v1.3 | 20/20 | Complete | 2026-02-19 |
| 27-36 | v2.0 | 27/27 | Complete | 2026-02-25 |
| 37 | v2.1 | 3/3 | Complete | 2026-02-25 |
| 38. UI Polish & List Page Cleanup | v2.2 | 3/3 | Complete | 2026-02-27 |
| 39. Dashboard Modifications | 1/2 | In Progress|  | - |
| 40. Journal Report & Grid Behavior | v2.2 | 0/? | Not started | - |
| 41. Begin Prayer | v2.2 | 0/? | Not started | - |
| 42. Mission Supervisor Role | v2.2 | 0/? | Not started | - |

**Total:** 6 milestones shipped, 110 plans executed across 38 phases. v2.2 in progress (5 phases, 26 requirements).

---

*Last updated: 2026-02-27 (Phase 39 plans created)*
