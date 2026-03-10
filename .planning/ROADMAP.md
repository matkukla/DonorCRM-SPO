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
- [x] **Phase 39: Dashboard Modifications** - Remove stale text and tiles, tighten spacing, add chart toggle, and enable cross-section tile dragging (completed 2026-02-27)
- [x] **Phase 40: Journal Report & Grid Behavior** - Rebuild journal report with new metrics/charts and make grid stage checkboxes directly clickable (completed 2026-02-27)
- [x] **Phase 41: Begin Prayer** - Add a dedicated prayer session entry point that launches expanded Focus Mode (completed 2026-02-27)
- [x] **Phase 42: Mission Supervisor Role** - New role with scoped visibility, assignment management, and missionary dashboard selector (completed 2026-03-02)
- [x] **Phase 43: Roles Redesign** - Rename staff→missionary and mission_supervisor→supervisor, add Coach role, Admin Assignments page, My Team page with missionary profiles (completed 2026-03-04)

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
- [x] 39-01-PLAN.md — Backend layout persistence + chart toggle + text/tile removals (DASH-01, DASH-04, DASH-05, DASH-06)
- [x] 39-02-PLAN.md — Flat grid restructure + spacing + backend persistence integration (DASH-02, DASH-03)

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
**Plans**: 1 plan

Plans:
- [ ] 41-01-PLAN.md — Begin Prayer button + intention selection dialog + Focus Mode wiring (PRAY-01)

### Phase 42: Mission Supervisor Role
**Goal**: Organization leadership can assign supervisors to missionaries, and supervisors see only their assigned missionaries' data across the entire application
**Depends on**: Phases 38-41 (execute last to avoid merge conflicts with Q helper refactor across 40+ views)
**Requirements**: SUPV-01, SUPV-02, SUPV-03, SUPV-04
**Success Criteria** (what must be TRUE):
  1. Mission Supervisor exists as a selectable role in the system, and admin can assign it to a user
  2. Admin can assign specific missionaries to a supervisor via the user management UI
  3. A supervisor sees only their assigned missionaries' data on all pages (contacts, gifts, recurring gifts, tasks, journals, prayers, analytics)
  4. Admin and supervisor can select a missionary from a dropdown and view that missionary's personal dashboard
**Plans**: 5 plans (completed 2026-03-02)

Plans:
- [x] 42-01-PLAN.md — Backend foundation: UserRole + supervisor FK + migration + get_visible_user_ids() helper + permission class + serializer updates (SUPV-01, SUPV-02)
- [x] 42-02-PLAN.md — Backend view scoping: update all get_queryset() methods across 13 view/service files to use centralized helper (SUPV-03)
- [x] 42-03-PLAN.md — Frontend types + role hierarchy + admin missionary assignment UI (SUPV-01, SUPV-02)
- [x] 42-04-PLAN.md — Dashboard missionary selector + supervisor dashboard view (SUPV-04)
- [x] 42-05-PLAN.md — List page owner columns + owner filters + read-only gating (SUPV-03)

### Phase 43: Roles Redesign
**Goal**: Rename roles to clearer names, add Coach role with limited visibility, and provide admin tools for managing assignments alongside supervisor/coach team views
**Depends on**: Phase 42 (extends supervisor role foundation)
**Requirements**: ROLE-01, ROLE-02, ROLE-03, ROLE-04, ROLE-05
**Success Criteria** (what must be TRUE):
  1. DB and UI use `missionary` (not `staff`) and `supervisor` (not `mission_supervisor`) everywhere
  2. Admin can assign both a supervisor and a coach to each missionary via `/admin/assignments`
  3. Coach role sees contacts + journals for assigned missionaries, but NOT gifts/pledges/donations
  4. Supervisors and coaches see a `/team` page listing their assigned missionaries
  5. Clicking a missionary on the team page opens a read-only profile with tabbed content
**Plans**: 5 plans

Plans:
- [ ] 43-01-PLAN.md — DB migration: rename roles, add coach FK, update model/permissions/serializers (ROLE-01, ROLE-02)
- [ ] 43-02-PLAN.md — Backend views: coach financial block, owner filter expansion, Assignments API (ROLE-02, ROLE-03)
- [ ] 43-03-PLAN.md — Frontend types + role rename sweep + coach UI checks across all pages (ROLE-01, ROLE-02, ROLE-03)
- [ ] 43-04-PLAN.md — Admin Assignments page: inline editable table with bulk operations (ROLE-04)
- [ ] 43-05-PLAN.md — My Team page + Missionary profile page with tabbed read-only content (ROLE-05)

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
| 39. Dashboard Modifications | v2.2 | Complete    | 2026-02-27 | 2026-02-27 |
| 40. Journal Report & Grid Behavior | 2/2 | Complete    | 2026-02-27 | - |
| 41. Begin Prayer | 1/1 | Complete    | 2026-02-27 | - |
| 42. Mission Supervisor Role | 5/5 | Complete    | 2026-03-02 | - |
| 43. Roles Redesign | 5/5 | Complete    | 2026-03-04 | - |

**Total:** 6 milestones shipped, 112 plans executed across 42 phases. v2.2 in progress (6 phases, 31 requirements).

### Phase 44: Modify the SPO data import and reconciliation workflow

**Goal:** Build a three-step SPO import pipeline (missionary reconciliation, gift attribution, prayer extraction) with MissionaryAlias name matching, anonymous donor handling, tri-source comparison, and full audit trail
**Requirements**: SPO-FOUNDATION, SPO-RECONCILE, SPO-GIFTS, SPO-PRAYERS, SPO-CLI, SPO-API
**Depends on:** Phase 43
**Plans:** 4/4 plans complete

Plans:
- [ ] 44-01-PLAN.md — MissionaryAlias model + SPO ImportBatchType choices + migration + admin + test stubs (SPO-FOUNDATION)
- [ ] 44-02-PLAN.md — reconcile_missionaries() service: three-level name matching, tri-source comparison, audit output (SPO-RECONCILE)
- [ ] 44-03-PLAN.md — import_spo_gifts() + import_spo_prayers() services: gift attribution, anonymous donor handling, prayer extraction (SPO-GIFTS, SPO-PRAYERS)
- [ ] 44-04-PLAN.md — Three management commands + three API views + URL routes (SPO-CLI, SPO-API)

### Phase 45: Fix backend-to-frontend data mapping issues

**Goal:** Org-type contacts (first_name and last_name blank, organization_name populated) display correctly across the entire application — in the contact list, search, CSV export, contact detail view, and create/edit form
**Requirements**: ORG-01, ORG-02, ORG-03, ORG-04, ORG-05
**Depends on:** Phase 44
**Plans:** 4/4 plans complete

Plans:
- [ ] 45-01-PLAN.md — Wave 0: test stubs in test_org_contact_mapping.py + OrgContactFactory (ORG-01 through ORG-05)
- [ ] 45-02-PLAN.md — Backend: full_name fallback + 3 serializers + 2 search paths + CSV export (ORG-01, ORG-02, ORG-03, ORG-04)
- [ ] 45-03-PLAN.md — Frontend: TypeScript interfaces + ContactForm field/validation + ContactDetail display (ORG-01, ORG-03, ORG-05)
- [ ] 45-04-PLAN.md — Human verification checkpoint: end-to-end org contact create/view/edit/search (ORG-01 through ORG-05)

### Phase 46: Multiple supervisors per missionary

**Goal:** Convert supervisor and coach relationships from ForeignKey to ManyToMany so each missionary can have multiple supervisors and coaches; update assignment UI with multi-select chips and a supervisor view toggle
**Requirements**: SUPV-01, SUPV-02, SUPV-03
**Depends on:** Phase 45
**Plans:** 6/6 plans complete

Plans:
- [ ] 46-01-PLAN.md — Wave 0: test stubs (test_m2m_assignments.py) + SupervisorUserFactory + CoachUserFactory (SUPV-01, SUPV-02, SUPV-03)
- [ ] 46-02-PLAN.md — DB migration + User model: FK→M2M with data preservation (SUPV-01, SUPV-02)
- [ ] 46-03-PLAN.md — Backend API layer: serializers + AssignmentsView arrays + additive flag (SUPV-02, SUPV-03)
- [ ] 46-04-PLAN.md — Frontend API types + AdminAssignments multi-select chips + view toggle (SUPV-02)
- [ ] 46-05-PLAN.md — AdminUsers.tsx: fix scalar FK assumptions, read from supervisor_ids/coach_ids arrays (SUPV-02)
- [ ] 46-06-PLAN.md — GAP: Role-filter supervisors/coaches in GET response + purge ghost M2M rows (SUPV-02)

### Phase 47: Fix Coach Role Gaps
**Goal:** Close critical v2.2 audit gaps — coach users can access contacts they're assigned to, test suite passes with correct role names, and coach assignments via AdminUsers page are persisted
**Requirements**: ROLE-01, ROLE-03, ROLE-04, ROLE-05
**Gap Closure:** Closes gaps from v2.2 audit
**Depends on:** Phase 46
**Plans:** 2/2 plans complete

Plans:
- [ ] 47-01-PLAN.md — Fix stale role='staff' in conftest.py and 3 test files (ROLE-01)
- [ ] 47-02-PLAN.md — Fix IsStaffOrAbove to allow coach safe-method access + regression tests for coached_user_ids M2M (ROLE-03, ROLE-04, ROLE-05)

---

*Last updated: 2026-03-10 (Phase 47 plans created)*
