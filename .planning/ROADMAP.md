# Roadmap: DonorCRM

## Milestones

- ✅ **v1.0 Journal Feature** — Phases 1-6 (shipped 2026-01-29)
- ✅ **v1.1 CSV Import** — Phases 7-12 (shipped 2026-02-04)
- ✅ **v1.2 Admin Analytics Dashboard** — Phases 13-19 (shipped 2026-02-16)
- ✅ **v1.3 Smartsheet Import, Filters & Polish** — Phases 20-26 (shipped 2026-02-19)
- ✅ **v2.0 Import Revamp, Prayer Intentions & Dashboard Polish** — Phases 27-36 (shipped 2026-02-25)
- ✅ **v2.1 Security Hardening** — Phase 37 (shipped 2026-02-25)
- ✅ **v2.2 UI Polish, Journal Report & Supervisor Role** — Phases 38-47 (shipped 2026-03-11)
- ✅ **v2.3 Goal Tracking & View As** — Phases 48-56 (shipped 2026-03-25)

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

<details>
<summary>v2.3 Goal Tracking & View As (Phases 48-56) — SHIPPED 2026-03-25</summary>

See milestones/v2.3-ROADMAP.md for complete phase details.

**Key Features:**
- Goal page with fiscal-year progress tracking, journal selection, pacing targets, and progress bars
- View As mode with read-only enforcement for supervisor/admin oversight
- Data scoping: admin/supervisor default to own data, cross-user access only via View As
- MPD dashboard enhancements: Monthly Average tile + Admin MPD Overview
- MPD Resources standalone page with pacing calculator
- Scheduled pipeline stage in journal system (7-stage pipeline)
- Task Broadcasting: admin/supervisor task distribution with completion tracking

**Scope:** 29 requirements, 9 phases (48-56), 31 plans

</details>

### Phase 01: Duplicate Contact Checking & Merging (GitHub issue #37)

| Plan | Description | Status |
|------|-------------|--------|
| 01 | Backend Foundation: models, migration, services | Complete |
| 02 | API Endpoints: duplicate check, scan, merge | Planned |
| 03 | Frontend: Duplicate Review Page | Planned |
| 04 | Frontend: Merge Dialog | Planned |
| 05 | Frontend: Creation-Time Warning | Planned |
| 06 | Integration Testing & Polish | Planned |

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 | 1-6 | 24 | Complete | 2026-01-29 |
| v1.1 | 7-12 | 15 | Complete | 2026-02-04 |
| v1.2 | 13-19 | 18 | Complete | 2026-02-16 |
| v1.3 | 20-26 | 20 | Complete | 2026-02-19 |
| v2.0 | 27-36 | 27 | Complete | 2026-02-25 |
| v2.1 | 37 | 3 | Complete | 2026-02-25 |
| v2.2 | 38-47 | 34 | Complete | 2026-03-11 |
| v2.3 | 48-56 | 31 | Complete | 2026-03-25 |

**Total:** 8 milestones shipped, 172 plans executed across 56 phases.
**Current:** Phase 01 — Duplicate Contact Checking & Merging (1/6 plans complete)

### Phase 1: Duplicate Contact Checking + Merging (GitHub issue #37)

**Goal:** Implement duplicate contact detection and merging so missionaries can keep their contact lists clean, with creation-time warnings, batch scan, side-by-side merge UI, and audit trail.
**Requirements**: [DUP-01, DUP-02, DUP-03, DUP-04, DUP-05, DUP-06, DUP-07, DUP-08]
**Depends on:** None (standalone feature)
**Plans:** 6 plans

Plans:
- [ ] 01-01-PLAN.md — Backend foundation: models, migration (pg_trgm), services (detect + merge)
- [ ] 01-02-PLAN.md — Backend API: serializers, views, URLs for check/scan/merge/dismiss
- [ ] 01-03-PLAN.md — Frontend setup: shadcn components, types, API functions, hooks
- [ ] 01-04-PLAN.md — Duplicate list page, ConfidenceBadge, sidebar nav, routing
- [ ] 01-05-PLAN.md — Merge view: side-by-side comparison, field overrides, confirmation
- [ ] 01-06-PLAN.md — Creation-time duplicate warning in ContactForm

---

*Last updated: 2026-03-27 (Phase 01 Plan 01 complete)*
