# Roadmap: DonorCRM

## Milestones

- **v1.0 Journal Feature** - Phases 1-6 (shipped 2026-01-29)
- **v1.1 CSV Import** - Phases 7-12 (shipped 2026-02-04)
- **v1.2 Admin Analytics Dashboard** - Phases 13-19 (in progress)

## Phases

<details>
<summary>v1.0 Journal Feature (Phases 1-6) - SHIPPED 2026-01-29</summary>

See milestones/v1.0-ROADMAP.md for complete phase details.

**Key Features:**
- Journal CRUD with owner-scoped visibility
- Contact membership management (many-to-many)
- 6-stage pipeline: Contact -> Meet -> Close -> Decision -> Thank -> Next Steps
- Decision tracking with history (dual-table pattern)
- Interactive grid UI with stage cell indicators
- Event timeline drawer with infinite scroll
- Analytics charts (decision trends, stage activity, pipeline breakdown)
- Contact detail integration (Journals tab)
- Task system integration (journal-linked tasks)
- Admin analytics endpoints

**Scope:** 19 requirements, 6 phases, 24 plans, 35 UAT tests passed

</details>

<details>
<summary>v1.1 CSV Import (Phases 7-12) - SHIPPED 2026-02-04</summary>

**Milestone Goal:** Enable admins to import SPO-exported CSV files (Funds, Entities, Transactions, Pledges) into DonorCRM with validation, preview, and idempotent upserts.

**Key Features:**
- Import Center UI for 4 CSV types
- Fund model for account/campaign tracking
- External ID support for idempotent imports
- Row-level validation and error reporting
- Import audit trail (ImportRun, ImportRowError)

**Scope:** 19 requirements, 6 phases, 15 plans

See full phase details in main ROADMAP.md history or milestones/v1.1-ROADMAP.md.

</details>

### v1.2 Admin Analytics Dashboard (In Progress)

**Milestone Goal:** Give coaches and leadership cross-missionary visibility into fundraising activity, pipeline health, and stalled contacts — so they can proactively support their teams.

**Target features:**
- Dashboard Overview page with summary cards, team activity table, conversion funnel, trend chart, and alerts panel
- Stalled Contacts page with 14+ day inactivity detection, pagination, and sorting
- User Detail page with per-missionary performance trends and journal listings
- User Drilldown panel (slide-in sidebar for quick inspection)
- 5 API endpoints with ADMIN/FINANCE role-based visibility
- Drill-down charts (click funnel segments to see underlying contacts)
- Comparison mode (time periods or users side-by-side)
- Activity heatmap calendar view

---

#### Phase 13: Backend Foundation & Security
**Goal:** Establish secure, performant analytics endpoints with fixed permission vulnerabilities and data integrity issues.

**Depends on:** Phase 12 (v1.1 CSV Import complete)

**Requirements:** API-01, API-02, API-03, API-04, API-05

**Success Criteria** (what must be TRUE):
  1. All admin analytics endpoints enforce ADMIN role-based access (non-admin users receive 403)
  2. Permission classes implement both has_permission() and has_object_permission() to prevent ListAPIView bypass
  3. Admin analytics endpoints use database-level aggregation with <20 queries per endpoint
  4. Stalled contact detection uses Subquery annotation to find contacts with last activity >14 days ago
  5. Existing race conditions in update_giving_stats() and record_fulfillment() are fixed (F() expressions, signal disable during bulk ops)

**Plans:** 2 plans

Plans:
- [x] 13-01-PLAN.md -- Fix race conditions and standardize permission classes on existing admin endpoints
- [x] 13-02-PLAN.md -- Create 5 admin analytics endpoints with service functions, URLs, and tests

---

#### Phase 14: Core Analytics Endpoints
**Goal:** Deliver 5 backend analytics endpoints serving aggregated data across all missionaries.

**Depends on:** Phase 13

**Requirements:** API-01, CMON-01, CMON-03, PIPE-01, USER-01

**Success Criteria** (what must be TRUE):
  1. AdminDashboardView returns summary cards (total contacts, active journals, conversion rate, stalled contacts count)
  2. StalledContactsView returns paginated list of contacts with 14+ days no activity (includes zero-activity contacts)
  3. UserPerformanceView returns per-missionary metrics (total contacts, active journals, decisions logged, conversion rate, donations)
  4. ConversionFunnelView returns pipeline stage distribution with counts and percentages across all missionaries
  5. TeamActivityView returns recent activity across all users (journal updates, new contacts, decisions logged)

**Plans:** TBD

Plans:
- [ ] 14-01-PLAN.md
- [ ] 14-02-PLAN.md

---

#### Phase 15: Frontend Foundation & Routing
**Goal:** Admin analytics pages render with API data and navigation integrated.

**Depends on:** Phase 14

**Requirements:** None (infrastructure)

**Success Criteria** (what must be TRUE):
  1. Admin can navigate to /admin/analytics/dashboard route (visible only to ADMIN users)
  2. Admin can navigate to /admin/analytics/stalled route
  3. Admin can navigate to /admin/analytics/users/:id route
  4. React Query hooks successfully fetch data from all 5 analytics endpoints
  5. Navigation menu displays "Analytics" submenu under Admin section (Users, Import Center, Analytics)

**Plans:** TBD

Plans:
- [ ] 15-01-PLAN.md
- [ ] 15-02-PLAN.md

---

#### Phase 16: Dashboard Overview Page
**Goal:** Admin can view Dashboard Overview page with all core widgets functional.

**Depends on:** Phase 15

**Requirements:** DASH-01, DASH-02, DASH-03, DASH-04, PIPE-01, USER-01

**Success Criteria** (what must be TRUE):
  1. Dashboard Overview displays summary cards showing total contacts, active journals, conversion rate, and stalled contacts count
  2. Dashboard Overview displays Team Activity Table showing recent actions (sortable by date and user)
  3. Dashboard Overview displays Alerts Panel with rule-based coaching prompts (e.g., "Sarah has 8 contacts stalled >21 days")
  4. Dashboard Overview displays Trend Charts (line chart) showing team metrics over past 12 weeks
  5. Dashboard Overview displays Conversion Funnel Chart showing pipeline stage distribution with counts and percentages

**Plans:** TBD

Plans:
- [ ] 16-01-PLAN.md
- [ ] 16-02-PLAN.md
- [ ] 16-03-PLAN.md

---

#### Phase 17: Stalled Contacts & User Detail Pages
**Goal:** Admin can monitor stalled contacts and inspect individual missionary performance.

**Depends on:** Phase 15

**Requirements:** CMON-01, CMON-02, CMON-03, USER-01, USER-02, USER-03

**Success Criteria** (what must be TRUE):
  1. Stalled Contacts page lists contacts with no activity in 14+ days (includes zero-activity contacts)
  2. Stalled Contacts page supports server-side pagination (50 per page) and sorting by days since last activity, contact name, and owner
  3. User Detail page displays per-missionary performance metrics (total contacts, active journals, decisions logged, conversion rate, donations)
  4. User Detail page shows trend charts for individual missionary (donations over time, stage activity over time)
  5. User Detail page lists missionary's journals with progress indicators

**Plans:** TBD

Plans:
- [ ] 17-01-PLAN.md
- [ ] 17-02-PLAN.md

---

#### Phase 18: Interactive Visualizations & Drill-Down
**Goal:** Admin can interact with charts to explore underlying data.

**Depends on:** Phase 16, Phase 17

**Requirements:** PIPE-02, USER-04, USER-05

**Success Criteria** (what must be TRUE):
  1. Admin can click funnel stage segment to drill down and see list of contacts currently in that stage
  2. Admin can open User Drilldown Panel (slide-in sidebar) from Team Activity Table for quick inspection
  3. User Drilldown Panel shows key stats, recent journal activity, and stalled contact count for selected missionary
  4. Drill-down panel displays without navigating away from current page
  5. Drill-down contact list loads data from backend endpoint filtered by stage parameter

**Plans:** TBD

Plans:
- [ ] 18-01-PLAN.md
- [ ] 18-02-PLAN.md

---

#### Phase 19: Advanced Features & Export
**Goal:** Admin can filter analytics by date range, compare time periods/users, view activity heatmap, and export data.

**Depends on:** Phase 18

**Requirements:** DATA-01, DATA-02, DATA-03, COMP-01, COMP-02, COMP-03

**Success Criteria** (what must be TRUE):
  1. Admin can filter all dashboard views by date range (presets: This Month, Last Quarter, YTD, Custom Range)
  2. Admin can export Stalled Contacts list and Team Activity data to CSV
  3. Admin can compare metrics across two time periods side-by-side with trend arrows showing change
  4. Admin can compare two missionaries side-by-side across key metrics
  5. Admin can view Activity Heatmap Calendar (GitHub-style contribution grid) showing team activity density by day

**Plans:** TBD

Plans:
- [ ] 19-01-PLAN.md
- [ ] 19-02-PLAN.md
- [ ] 19-03-PLAN.md

---

## Progress

**Execution Order:**
Phases execute in numeric order: 13 → 14 → 15 → 16 → 17 → 18 → 19

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6. v1.0 Journal | v1.0 | 24/24 | Complete | 2026-01-29 |
| 7. Foundation | v1.1 | 2/2 | Complete | 2026-01-30 |
| 8. Funds CSV Import | v1.1 | 2/2 | Complete | 2026-01-30 |
| 9. Entities CSV Import | v1.1 | 2/2 | Complete | 2026-02-01 |
| 10. Transactions CSV Import | v1.1 | 2/2 | Complete | 2026-02-02 |
| 11. Pledges CSV Import | v1.1 | 2/2 | Complete | 2026-02-03 |
| 12. Import Center UI | v1.1 | 5/5 | Complete | 2026-02-04 |
| 13. Backend Foundation & Security | v1.2 | 2/2 | Complete | 2026-02-12 |
| 14. Core Analytics Endpoints | v1.2 | 0/TBD | Not started | - |
| 15. Frontend Foundation & Routing | v1.2 | 0/TBD | Not started | - |
| 16. Dashboard Overview Page | v1.2 | 0/TBD | Not started | - |
| 17. Stalled Contacts & User Detail Pages | v1.2 | 0/TBD | Not started | - |
| 18. Interactive Visualizations & Drill-Down | v1.2 | 0/TBD | Not started | - |
| 19. Advanced Features & Export | v1.2 | 0/TBD | Not started | - |

---

*Last updated: 2026-02-12 (Phase 13 complete - 2/2 plans executed, verified)*
