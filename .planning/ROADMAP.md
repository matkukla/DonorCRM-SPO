# Roadmap: DonorCRM

## Milestones

- ✅ **v1.0 Journal Feature** -- Phases 1-6 (shipped 2026-01-29)
- ✅ **v1.1 CSV Import** -- Phases 7-12 (shipped 2026-02-04)
- ✅ **v1.2 Admin Analytics Dashboard** -- Phases 13-19 (shipped 2026-02-16)
- ✅ **v1.3 Smartsheet Import, Filters & Polish** -- Phases 20-26 (shipped 2026-02-19)
- ✅ **v2.0 Import Revamp, Prayer Intentions & Dashboard Polish** -- Phases 27-36 (shipped 2026-02-25)

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

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1.0 | 24/24 | Complete | 2026-01-29 |
| 7-12 | v1.1 | 15/15 | Complete | 2026-02-04 |
| 13-19 | v1.2 | 18/18 | Complete | 2026-02-16 |
| 20-26 | v1.3 | 20/20 | Complete | 2026-02-19 |
| 27-36 | v2.0 | 27/27 | Complete | 2026-02-25 |

**Total:** 5 milestones shipped, 104 plans executed across 36 phases

### Phase 37: Full Security Check

**Goal:** Harden DonorCRM against common security vulnerabilities (auth brute-force, missing headers, broken token rotation, weak passwords, known CVEs) with a documented security report
**Depends on:** Phase 36
**Plans:** 2/3 plans executed

Plans:
- [ ] 37-01-PLAN.md -- Auth hardening: rate limiting, refresh token rotation fix, password validator
- [ ] 37-02-PLAN.md -- Security headers (CSP, Referrer-Policy) and API docs restriction
- [ ] 37-03-PLAN.md -- Automated scanning (bandit, pip-audit, npm audit), secrets audit, SECURITY-REPORT.md

---

*Last updated: 2026-02-25 (Phase 37 planned)*
