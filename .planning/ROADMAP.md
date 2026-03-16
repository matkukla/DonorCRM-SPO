# Roadmap: DonorCRM

## Milestones

- ✅ **v1.0 Journal Feature** — Phases 1-6 (shipped 2026-01-29)
- ✅ **v1.1 CSV Import** — Phases 7-12 (shipped 2026-02-04)
- ✅ **v1.2 Admin Analytics Dashboard** — Phases 13-19 (shipped 2026-02-16)
- ✅ **v1.3 Smartsheet Import, Filters & Polish** — Phases 20-26 (shipped 2026-02-19)
- ✅ **v2.0 Import Revamp, Prayer Intentions & Dashboard Polish** — Phases 27-36 (shipped 2026-02-25)
- ✅ **v2.1 Security Hardening** — Phase 37 (shipped 2026-02-25)
- ✅ **v2.2 UI Polish, Journal Report & Supervisor Role** — Phases 38-47 (shipped 2026-03-11)
- 🚧 **v2.3 Goal Tracking & View As** — Phases 48-54 (in progress)

## Phases

<details>
<summary>v1.0 Journal Feature (Phases 1-6) — SHIPPED 2026-01-29</summary>

See milestones/v1.0-ROADMAP.md for complete phase details.

**Key Features:**
- Journal CRUD with owner-scoped visibility
- 6-stage pipeline with decision tracking
- Interactive grid UI with analytics charts
- Contact detail integration and task system

**Scope:** 19 requirements, 6 phases, 24 plans

</details>

<details>
<summary>v1.1 CSV Import (Phases 7-12) — SHIPPED 2026-02-04</summary>

See milestones/v1.1-ROADMAP.md for complete phase details.

**Key Features:**
- Import Center UI for 4 CSV types
- Fund model, external IDs, import audit trail

**Scope:** 19 requirements, 6 phases, 15 plans

</details>

<details>
<summary>v1.2 Admin Analytics Dashboard (Phases 13-19) — SHIPPED 2026-02-16</summary>

See milestones/v1.2-ROADMAP.md for complete phase details.

**Key Features:**
- Dashboard Overview with summary cards, trend charts, conversion funnel
- Stalled Contacts monitoring, User Detail pages
- Interactive drill-down, heatmap, time period comparison

**Scope:** 26 requirements, 7 phases, 18 plans

</details>

<details>
<summary>v1.3 Smartsheet Import, Filters & Polish (Phases 20-26) — SHIPPED 2026-02-19</summary>

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
<summary>v2.0 Import Revamp, Prayer Intentions & Dashboard Polish (Phases 27-36) — SHIPPED 2026-02-25</summary>

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
<summary>v2.1 Security Hardening (Phase 37) — SHIPPED 2026-02-25</summary>

See milestones/v2.1-ROADMAP.md for complete phase details.

**Key Features:**
- Auth rate limiting and refresh token rotation fix
- Content-Security-Policy, Referrer-Policy, Permissions-Policy headers
- API docs authentication gate in production
- Python and JS dependency CVE patches
- Comprehensive SECURITY-REPORT.md

**Scope:** 1 phase, 3 plans, 6 tasks

</details>

<details>
<summary>v2.2 UI Polish, Journal Report & Supervisor Role (Phases 38-47) — SHIPPED 2026-03-11</summary>

See milestones/v2.2-ROADMAP.md for complete phase details.

**Key Features:**
- UI polish: centered dialogs, "Potential Donor" rename, gift list Type column, analytics cleanup
- Dashboard: bar/line chart toggle, cross-section drag, tightened gaps, removed stale tiles
- Journal report rebuilt with metrics cards, charts, conditional alerts; single-click stage checkbox
- Begin Prayer: "Begin Prayer" button launching expanded Focus Mode with intention selection
- Mission Supervisor and Coach roles with scoped visibility, M2M assignments (multiple per missionary)
- Roles Redesign: staff→missionary, mission_supervisor→supervisor, Coach role, Admin Assignments, My Team
- SPO import pipeline with MissionaryAlias name matching and full audit trail (CLI/API)
- Org contact data mapping: organization_name across all views and export
- Coach role gaps closed: permission fixes, coached_user_ids M2M, stale role strings fixed

**Scope:** 36 requirements, 10 phases (38-47), 34 plans

</details>

### 🚧 v2.3 Goal Tracking & View As (In Progress)

**Milestone Goal:** Give missionaries a dedicated Goal page to track fundraising progress, and give supervisors/admins a View As mode to see any missionary's data in read-only.

## Phase Details

### Phase 48: MPD Dashboard Enhancements
**Goal**: The dashboard MPD section is enriched with a Monthly Average tile visible to all users, and an Admin MPD Overview section visible only to admin showing org-wide MPD health
**Depends on**: Phase 47 (v2.2 complete)
**Requirements**: MPD-01, MPD-02
**Success Criteria** (what must be TRUE):
  1. The MPD Financial Overview section on the dashboard shows a "Monthly Average" tile displaying the user's average monthly giving calculated from Smartsheet MPD data
  2. Admin users see an additional "MPD Overview" section on the dashboard showing org-wide MPD health metrics aggregated from all missionaries' Smartsheet snapshots
  3. Non-admin users do not see the MPD Overview section
**Plans**: 2 plans
Plans:
- [ ] 48-01-PLAN.md — Backend: add monthly_average to MPDMyDataView and MPDOverviewView with tests
- [ ] 48-02-PLAN.md — Frontend: Monthly Average tile, 4-col grid, admin MPD Overview table section

### Phase 49: Goal Page — Data Model & Backend
**Goal**: The backend infrastructure for Goal tracking exists: fiscal year utility, goal data models, and API endpoints that correctly calculate support progress from selected journals
**Depends on**: Phase 48
**Requirements**: FISC-01, FISC-02, GOAL-02, GOAL-03, GOAL-04, GOAL-11
**Success Criteria** (what must be TRUE):
  1. A fiscal_year_utils module exists with July 1 start logic and a months_remaining() function that returns a minimum of 1
  2. Missionary can set and save their monthly support goal in dollars via the API, persisted as cents on the User model
  3. Missionary can save a list of journals that count toward their goal, with selections persisted per user in GoalJournalSelection
  4. Missionary can save the number of weeks to accomplish their goal (goalWeeks), persisted on the User model alongside the monthly support goal
  5. The goal detail API endpoint returns calculated effective monthly support (monthly pledges + one-time gifts divided by months remaining in fiscal year) from the selected journals
  6. The monthly support goal field is removed from the Settings page or replaced with a link to the Goal page
**Plans**: 4 plans
Plans:
- [ ] 49-01-PLAN.md — Wave 0: test scaffolds (test_fiscal_year, test_goal_services, test_views_goals, factory update)
- [ ] 49-02-PLAN.md — Wave 1: fiscal_year.py utility + extract _monthly_equivalent_aggregate to core/gift_utils.py
- [ ] 49-03-PLAN.md — Wave 2: migrations (rename monthly_goal → cents field, add goal_weeks, GoalJournalSelection) + all reference updates
- [ ] 49-04-PLAN.md — Wave 3: goal_services.py + GoalView + /api/v1/goals/me/ endpoint

### Phase 50: Goal Page — Frontend UI
**Goal**: Missionaries can navigate to and fully interact with the Goal page, including progress bars, pacing targets, milestone messages, and read-only mode for supervisors and admins
**Depends on**: Phase 49
**Requirements**: GOAL-01, GOAL-05, GOAL-06, GOAL-07, GOAL-08, GOAL-09, GOAL-10
**Success Criteria** (what must be TRUE):
  1. A "Goal" link appears in the sidebar below Dashboard and routes to the Goal page
  2. The Goal page displays three progress bars (Monthly Support $, Calls Completed, Meetings Held) each with 25/50/75/100% milestone markers
  3. Monthly Support bar changes color based on threshold: red below 75%, green 75–99%, honey gold at 100%
  4. Pacing targets (Partners Needed = Goal ÷ $80 avg gift; Calls = Partners × 9; Appts = Partners × 1.5; Appts per Week = Appts ÷ goalWeeks) appear when a goal and journals are selected
  5. Motivational milestone messages appear at 0%, 25%, 50%, 75%, and 100% progress; empty-state messages appear when no goal is set or no journals are selected
  6. Supervisor and admin users see the Goal page in read-only mode — goal amount and journal selections cannot be edited
**Plans**: 5 plans
Plans:
- [ ] 50-01-PLAN.md — Wave 1: backend fields (calls_completed, meetings_held), migration, views_goals PATCH, tests
- [ ] 50-02-PLAN.md — Wave 1: GoalProgressBar component with tick marks and dynamic color
- [ ] 50-03-PLAN.md — Wave 2: goals.ts API client + useGoal.ts React Query hooks
- [ ] 50-04-PLAN.md — Wave 3: Sidebar nav, lazy route, GoalPage (Settings, Progress, Pacing cards)
- [ ] 50-05-PLAN.md — Wave 4: checkpoint human verification

### Phase 51: Data Scoping — Admin & Supervisor Default to Own Data
**Goal**: Admin and supervisor roles default to seeing only their own data across all list views, identical to missionary behavior — elevated cross-user access is no longer the default
**Depends on**: Phase 47 (v2.2 complete; can run in parallel with 49–50)
**Requirements**: SCOPE-01, SCOPE-02
**Success Criteria** (what must be TRUE):
  1. An admin user logging in sees only their own contacts, gifts, journals, tasks, and prayers — not all users' data
  2. A supervisor user logging in sees only their own data by default — not their assigned missionaries' data
  3. Cross-user data access activates only when a View As session is explicitly started — no other pathway unlocks it
**Plans**: 2 plans
Plans:
- [ ] 51-01-PLAN.md — Wave 1: test scaffold for get_visible_user_ids() covering all 6 roles (RED state)
- [ ] 51-02-PLAN.md — Wave 2: implement scoping change in permissions.py + fix breaking test

### Phase 52: View As — Backend
**Goal**: The backend can validate View As permissions, return the correct list of viewable users per role, and block all mutating requests when the X-View-As-User-Id header is present
**Depends on**: Phase 51
**Requirements**: VIEWAS-07, VIEWAS-08, VIEWAS-12
**Success Criteria** (what must be TRUE):
  1. GET /api/users/viewable returns all missionaries for admin; returns only assigned missionaries for supervisor
  2. Any POST, PUT, PATCH, or DELETE request sent with the X-View-As-User-Id header returns 403 Forbidden
  3. A supervisor sending X-View-As-User-Id for a missionary not in their assigned list receives 403 Forbidden; an admin is never blocked by this check
**Plans**: TBD

### Phase 53: View As — Frontend
**Goal**: Admins and supervisors can enter View As mode via a selector, see all data belonging to the selected missionary, and exit cleanly — with mutations blocked throughout the session
**Depends on**: Phase 52
**Requirements**: VIEWAS-01, VIEWAS-02, VIEWAS-03, VIEWAS-04, VIEWAS-05, VIEWAS-06, VIEWAS-09, VIEWAS-10, VIEWAS-11
**Success Criteria** (what must be TRUE):
  1. Admin sees a "View As" dropdown listing all missionaries; supervisor sees only their assigned missionaries; missionaries see no dropdown
  2. Selecting a missionary triggers a persistent banner showing the missionary's name, a read-only indicator, and an Exit button
  3. All data visible on every page (contacts, journals, gifts, dashboard, prayers, tasks) belongs to the selected missionary while in View As mode
  4. All create, edit, and delete actions are disabled or hidden for the duration of the View As session; admin-only navigation sections (user management, import, analytics admin) are also hidden
  5. View As selection persists across page navigation until the Exit button is clicked; all React Query caches are invalidated when the selected user changes
**Plans**: TBD

### Phase 54: MPD Resources Tab
**Goal**: Missionaries, supervisors, and admins can access a standalone MPD Resources page with an interactive Support Raising Calculator that computes pacing targets in real-time from a goal amount and weeks input
**Depends on**: Phase 48 (MPD foundation; can run in parallel with 49–53)
**Requirements**: MPD-CALC-01
**Success Criteria** (what must be TRUE):
  1. An "MPD Resources" nav item appears in the sidebar directly under "Insights" and routes to /mpd-resources
  2. The Support Raising Calculator displays a 2-column grid with 2 inputs (Amount to Raise, Number of Weeks) and 6 read-only outputs (Name-storming, Phone Calls, Phone Convos, Scheduled Appts, Mission Partners, Appts per Week)
  3. All outputs update in real-time as inputs change, using centralized constants in frontend/src/config/mpdCalculator.ts (DEFAULT_AVG_GIFT_DOLLARS: 80, NAMES_PER_PARTNER: 4.5, CALLS_PER_PARTNER: 9, CONVOS_PER_PARTNER: 3, APPTS_PER_PARTNER: 1.5)
  4. A "More Resources Coming Soon" placeholder card appears below the calculator
  5. The layout is responsive (single column on mobile)
**Plans**: 1 plan

## Summary Checklist

- [x] **Phase 48: MPD Dashboard Enhancements** - Monthly Average tile and Admin MPD Overview section (completed 2026-03-12)
- [x] **Phase 49: Goal Page — Data Model & Backend** - Fiscal year utility, User.monthly_support_goal_cents, GoalJournalSelection model, and goal calculation API endpoints (completed 2026-03-13)
- [ ] **Phase 50: Goal Page — Frontend UI** - Goal page with progress bars, pacing targets, milestone messages, sidebar nav, and read-only mode
- [x] **Phase 51: Data Scoping** - Admin and supervisor default to own data; cross-user access only via View As (completed 2026-03-16)
- [ ] **Phase 52: View As — Backend** - X-View-As-User-Id middleware, permission checks, mutation blocking, viewable users endpoint
- [ ] **Phase 53: View As — Frontend** - ViewAsContext, API header injection, persistent banner, selector, nav hiding, cache invalidation
- [ ] **Phase 54: MPD Resources Tab** - MPD Resources nav item under Insights, Support Raising Calculator with real-time pacing outputs, centralized constants in mpdCalculator.ts

## Progress

**Execution Order:** 48 → 49 → 50 → 51 → 52 → 53 → 54
(Phase 54 can also run in parallel with 49–53 as it's pure frontend with no backend dependencies)
(Phase 51 can run in parallel with 49–50; phases 52–53 depend on 51)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1.0 | 24/24 | Complete | 2026-01-29 |
| 7-12 | v1.1 | 15/15 | Complete | 2026-02-04 |
| 13-19 | v1.2 | 18/18 | Complete | 2026-02-16 |
| 20-26 | v1.3 | 20/20 | Complete | 2026-02-19 |
| 27-36 | v2.0 | 27/27 | Complete | 2026-02-25 |
| 37 | v2.1 | 3/3 | Complete | 2026-02-25 |
| 38-47 | v2.2 | 34/34 | Complete | 2026-03-11 |
| 48. MPD Dashboard Enhancements | v2.3 | 2/2 | Complete | 2026-03-12 |
| 49. Goal Page — Data Model & Backend | 4/4 | Complete    | 2026-03-13 | - |
| 50. Goal Page — Frontend UI | 4/5 | In Progress|  | - |
| 51. Data Scoping | 2/2 | Complete   | 2026-03-16 | - |
| 52. View As — Backend | v2.3 | 0/TBD | Not started | - |
| 53. View As — Frontend | v2.3 | 0/TBD | Not started | - |
| 54. MPD Resources Tab | v2.3 | 0/1 | Not started | - |

**Total:** 7 milestones shipped, 141 plans executed across 47 phases. v2.3 in progress (1/7 phases complete).

---

*Last updated: 2026-03-12 (Phase 49 planned — 4 plans; Phase 48 complete)*
