# Requirements: v1.2 Admin Analytics Dashboard

**Milestone:** v1.2
**Goal:** Give coaches and leadership cross-missionary visibility into fundraising activity, pipeline health, and stalled contacts — so they can proactively support their teams.
**Target Users:** 10-20 coaches/supervisors monitoring missionaries

---

## v1.2 Requirements

### Dashboard Core (DASH)

- [ ] **DASH-01**: Admin can view a Dashboard Overview page with summary cards showing total contacts, active journals, conversion rate, and stalled contacts count across all missionaries
- [ ] **DASH-02**: Admin can view a Team Activity Table showing all missionaries' recent actions (journal updates, new contacts, decisions logged), sortable by date and user
- [ ] **DASH-03**: Admin can view an Alerts Panel with rule-based coaching prompts (e.g., "Sarah has 8 contacts stalled >21 days", "Team conversion dropped 10% this month")
- [ ] **DASH-04**: Admin can view Trend Charts (line chart) showing team metrics over the past 12 weeks (decisions logged, donations received, stage progressions)

### Pipeline Analytics (PIPE)

- [ ] **PIPE-01**: Admin can view a Conversion Funnel Chart showing aggregate pipeline stage distribution (contact → meet → close → decision → thank → next_steps) with counts and percentages across all missionaries
- [ ] **PIPE-02**: Admin can click a funnel stage segment to drill down and see the list of contacts currently in that stage (drill-down chart interaction)

### Contact Monitoring (CMON)

- [ ] **CMON-01**: Admin can view a Stalled Contacts page listing contacts with no journal stage event activity in 14+ days
- [ ] **CMON-02**: Stalled Contacts page supports server-side pagination (50 per page) and sorting by days since last activity, contact name, and owner
- [ ] **CMON-03**: Stalled contacts include contacts added to journals but with zero stage events (never activated)

### User Performance (USER)

- [ ] **USER-01**: Admin can view a User Detail page showing per-missionary performance metrics (total contacts, active journals, decisions logged, conversion rate, total donations)
- [ ] **USER-02**: User Detail page shows trend charts for the individual missionary (donations over time, stage activity over time)
- [ ] **USER-03**: User Detail page lists the missionary's journals with progress indicators
- [ ] **USER-04**: Admin can open a User Drilldown Panel (slide-in sidebar) from the Team Activity Table for quick inspection without navigating away
- [ ] **USER-05**: User Drilldown Panel shows key stats, recent journal activity, and stalled contact count for the selected missionary

### Comparison & Advanced Viz (COMP)

- [ ] **COMP-01**: Admin can compare metrics across two time periods side-by-side (e.g., "This Month vs Last Month") with trend arrows showing change
- [ ] **COMP-02**: Admin can compare two missionaries side-by-side across key metrics (contacts, decisions, conversion rate)
- [ ] **COMP-03**: Admin can view an Activity Heatmap Calendar (GitHub-style contribution grid) showing team activity density by day

### API & Access Control (API)

- [ ] **API-01**: 5 backend API endpoints serve admin analytics: dashboard overview, stalled contacts, user performance, conversion funnel, team activity
- [ ] **API-02**: All admin analytics endpoints enforce ADMIN role-based access (non-admin users receive 403)
- [ ] **API-03**: Admin analytics endpoints use database-level aggregation (annotate/aggregate) to avoid N+1 queries — target <20 queries per endpoint
- [ ] **API-04**: Stalled contact detection uses Subquery annotation on JournalStageEvent to find contacts with last activity >14 days ago
- [ ] **API-05**: Conversion funnel reuses existing Journal 6-stage pipeline (PipelineStage) with cross-user aggregation

### Data Management (DATA)

- [ ] **DATA-01**: Admin can filter all dashboard views by date range (preset: This Month, Last Quarter, YTD, Custom Range)
- [ ] **DATA-02**: Admin can export Stalled Contacts list and Team Activity data to CSV
- [ ] **DATA-03**: Pace calculation computes average days between stage transitions per contact

---

## Future Requirements (Deferred)

| Requirement | Deferred To | Reason |
|-------------|-------------|--------|
| Configurable alert thresholds (per coach) | v2.0 | Requires user preferences model |
| Goal setting & tracking UI | v1.3+ | Requires new Goal model, progress calculations |
| Saved filter views | v1.3+ | Nice-to-have, not critical for coaching |
| Email digest reports for coaches | v2.0 | No email infrastructure yet |

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time updates via WebSocket/SSE | Polling sufficient for 10-20 admin users |
| Email digest reports | No email infrastructure yet |
| Performance scoring/gamification | Could demotivate missionaries |
| Projected outcomes with confidence intervals | Over-engineering for v1.2 |
| Custom dashboard builder (drag-and-drop) | Coaches want answers, not tools to build dashboards |
| Bulk editing from dashboard | Dashboards are for visibility; bulk actions belong in management pages |
| Real-time collaboration (live cursors) | Coaches review data independently |
| Granular row-level permissions | Over-engineering for 10-20 coaches; role-based is sufficient |
| Org chart visualization | SPO structure is flat; simple team table suffices |
| AI-generated suggestions | Manual workflow only for v1.2 |
| Custom stage definitions | Fixed 6-stage pipeline |
| Historical drill-down beyond 24 months | Diminishing returns; coaching focuses on recent trends |

## Traceability

*Populated by roadmap — maps each requirement to a phase.*

| REQ | Phase | Status |
|-----|-------|--------|
| — | — | — |

---

*Generated: 2026-02-12 | 26 requirements across 7 categories*
