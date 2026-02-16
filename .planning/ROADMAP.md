# Roadmap: DonorCRM

## Milestones

- **v1.0 Journal Feature** - Phases 1-6 (shipped 2026-01-29)
- **v1.1 CSV Import** - Phases 7-12 (shipped 2026-02-04)
- **v1.2 Admin Analytics Dashboard** - Phases 13-19 (shipped 2026-02-16)

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

See milestones/v1.1-ROADMAP.md for complete phase details.

**Key Features:**
- Import Center UI for 4 CSV types
- Fund model for account/campaign tracking
- External ID support for idempotent imports
- Row-level validation and error reporting
- Import audit trail (ImportRun, ImportRowError)

**Scope:** 19 requirements, 6 phases, 15 plans

</details>

<details>
<summary>v1.2 Admin Analytics Dashboard (Phases 13-19) - SHIPPED 2026-02-16</summary>

See milestones/v1.2-ROADMAP.md for complete phase details.

**Key Features:**
- Dashboard Overview with summary cards, trend charts, conversion funnel, team activity, and coaching alerts
- Stalled Contacts monitoring (14+ day detection) with pagination and sorting
- Per-missionary User Detail pages with individual trend charts and journal listings
- Interactive drill-down: clickable funnel segments and user quick-view slide-in panels
- Date range filtering with presets, CSV exports for stalled contacts and team activity
- Activity heatmap calendar, time period comparison with trend arrows, user comparison

**Scope:** 26 requirements, 7 phases, 18 plans, 65 tasks, 10 UAT tests passed

</details>

## Progress

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
| 14. Core Analytics Endpoints | v1.2 | 2/2 | Complete | 2026-02-13 |
| 15. Frontend Foundation & Routing | v1.2 | 2/2 | Complete | 2026-02-13 |
| 16. Dashboard Overview Page | v1.2 | 3/3 | Complete | 2026-02-14 |
| 17. Stalled Contacts & User Detail Pages | v1.2 | 2/2 | Complete | 2026-02-14 |
| 18. Interactive Visualizations & Drill-Down | v1.2 | 2/2 | Complete | 2026-02-15 |
| 19. Advanced Features & Export | v1.2 | 4/4 | Complete | 2026-02-16 |

---

*Last updated: 2026-02-16 (v1.2 milestone complete)*
