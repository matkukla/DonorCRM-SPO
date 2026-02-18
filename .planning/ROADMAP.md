# Roadmap: DonorCRM

## Milestones

- **v1.0 Journal Feature** - Phases 1-6 (shipped 2026-01-29)
- **v1.1 CSV Import** - Phases 7-12 (shipped 2026-02-04)
- **v1.2 Admin Analytics Dashboard** - Phases 13-19 (shipped 2026-02-16)
- **v1.3 Smartsheet Import, Filters & Polish** - Phases 20-25 (in progress)

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

### v1.3 Smartsheet Import, Filters & Polish (In Progress)

**Milestone Goal:** Enable Smartsheet file import with column mapping, add comprehensive filtering across all list pages, and fix security/quality/dark mode issues.

- [x] **Phase 20: Security & Performance Fixes** - Fix permission bypasses, N+1 queries, file size limits, and data integrity bugs (completed 2026-02-17)
- [x] **Phase 21: Dark Mode & UI Polish** - Fix hardcoded colors, WCAG contrast, error boundaries, and CSV sanitization (completed 2026-02-17)
- [x] **Phase 22: Filter Infrastructure** - Build reusable filter system with URL persistence, presets, badges, CSV export, and server-side query optimization (completed 2026-02-17)
- [x] **Phase 23: Per-Page Filter Implementation** - Apply filters to contacts, donations, pledges, journals, and transactions pages (completed 2026-02-18)
- [ ] **Phase 24: Smartsheet Import Backend** - File upload, format detection, column mapping engine, validation, and sanitization
- [ ] **Phase 25: Smartsheet Import Frontend** - Import type selection, mapping UI with confidence indicators, preview, and saved templates

## Phase Details

### Phase 20: Security & Performance Fixes
**Goal**: All known security vulnerabilities and performance bottlenecks are resolved before new features are built
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: QAL-01, QAL-02, QAL-05, QAL-06, QAL-07, QAL-08, QAL-09
**Success Criteria** (what must be TRUE):
  1. Non-admin users can only see and modify their own data across all list endpoints (no permission bypass)
  2. Stage event creation rejects contacts not owned by the requesting user
  3. Journal grid page loads with fewer than 10 database queries regardless of data volume
  4. File upload endpoints reject files exceeding the configured size limit with a clear error message
  5. Frontend routes for admin-only pages redirect non-admin users to an appropriate page
**Plans**: 3 plans

Plans:
- [ ] 20-01-PLAN.md — Backend security fixes: permission scoping (QAL-01), cross-user contact validation (QAL-02), Decimal arithmetic (QAL-07)
- [ ] 20-02-PLAN.md — File upload limits (QAL-06) and frontend route guards with redirect + toast (QAL-08)
- [ ] 20-03-PLAN.md — N+1 query fix in journal grid (QAL-05) and dashboard GET side-effect removal (QAL-09)

### Phase 21: Dark Mode & UI Polish
**Goal**: The application looks correct and accessible in both light and dark mode, with resilient error handling
**Depends on**: Phase 20
**Requirements**: QAL-03, QAL-04, QAL-10, QAL-11, QAL-12
**Success Criteria** (what must be TRUE):
  1. All pages render with consistent colors in dark mode (no hardcoded light-only colors visible)
  2. All text meets WCAG 4.5:1 contrast ratio in both light and dark mode
  3. An unhandled React error on any page shows a user-friendly fallback instead of a white screen
  4. Editing a donation amount correctly updates the associated contact's lifetime and monthly stats
  5. Exported CSV files do not contain unsanitized formula characters that could execute in spreadsheet software
**Plans**: 3 plans

Plans:
- [x] 21-01-PLAN.md — Fix all 50 hardcoded dark mode colors across 12 files with paired dark: variants (QAL-03)
- [x] 21-02-PLAN.md — Fix donation edit stats bug (QAL-11) and CSV export formula sanitization (QAL-12)
- [x] 21-03-PLAN.md — React Error Boundary with fallback UI (QAL-10) and visual WCAG contrast verification (QAL-04)

### Phase 22: Filter Infrastructure
**Goal**: A reusable, server-side filter system exists that any list page can plug into with URL persistence, presets, and export
**Depends on**: Phase 21 (dark mode patterns established before new UI components)
**Requirements**: FLT-08, FLT-09, FLT-10, FLT-11, FLT-12, FLT-13
**Success Criteria** (what must be TRUE):
  1. Filter selections on any page are reflected in URL params that can be bookmarked and shared
  2. User can clear all active filters with a single click and the page shows unfiltered results
  3. User can select a filter preset (e.g., "This Month", "Needs Thank You") and see the corresponding filters applied
  4. Active filters are displayed as summary badges showing what is currently filtered
  5. User can export the currently filtered results to CSV (not the full unfiltered dataset)
**Plans**: 3 plans

Plans:
- [x] 22-01-PLAN.md — Backend FilterSets (django-filter 24.3 upgrade) + filtered CSV export endpoints for contacts, donations, pledges, tasks (FLT-13, FLT-12)
- [x] 22-02-PLAN.md — Frontend filter infrastructure: nuqs URL state, useFilterParams hook, FilterBar/FilterBadge/FilterPresets/ExportCSVButton components (FLT-09, FLT-10, FLT-11)
- [x] 22-03-PLAN.md — Wire infrastructure to ContactList (reference implementation) + fix Transactions FLT-08 bug (FLT-08)

### Phase 23: Per-Page Filter Implementation
**Goal**: Users can filter contacts, donations, pledges, journals, and transactions by the fields relevant to each page
**Depends on**: Phase 22 (filter infrastructure must exist)
**Requirements**: FLT-01, FLT-02, FLT-03, FLT-04, FLT-05, FLT-06, FLT-07
**Success Criteria** (what must be TRUE):
  1. User can filter donations, journals, pledges, and transactions by date range and see only matching records
  2. User can filter donations and pledges by amount range (min/max) and see only records within that range
  3. User can filter contacts by group membership and donations by payment method or fund
  4. Admin can filter contacts and donations by owner (missionary) to see a specific missionary's data
  5. User can filter journals by name, date range, and archived status, and pledges by frequency or donor name
**Plans**: 3 plans

Plans:
- [ ] 23-01-PLAN.md — Backend filter enhancements: add amount/fund/owner filters to DonationFilterSet, SearchFilter to pledges, create JournalFilterSet + export CSV, fund list endpoint
- [ ] 23-02-PLAN.md — Frontend DonationList + PledgeList: migrate to useFilterParams + FilterBar with all filter controls, presets, badges, export
- [ ] 23-03-PLAN.md — Frontend JournalList: migrate to useFilterParams + FilterBar with search, archived toggle, deadline range, presets, export (card grid preserved)

### Phase 24: Smartsheet Import Backend
**Goal**: The backend can accept Excel and CSV files, detect format, extract headers, apply column mappings, validate rows, and sanitize data
**Depends on**: Phase 20 (file size limits must be in place)
**Requirements**: IMP-01, IMP-02, IMP-05, IMP-08, IMP-09
**Success Criteria** (what must be TRUE):
  1. User can upload both .xlsx and .csv files and the system processes them correctly without manual format selection
  2. System returns extracted column headers and auto-detected field mappings with confidence scores for each column
  3. All rows are validated and errors are returned as a downloadable CSV with row numbers and error descriptions
  4. Formula injection characters (=, +, -, @) in imported cell values are stripped or escaped before storage
**Plans**: TBD

Plans:
- [ ] 24-01: TBD
- [ ] 24-02: TBD

### Phase 25: Smartsheet Import Frontend
**Goal**: Users can import Smartsheet exports through a guided wizard with column mapping, preview, and reusable templates
**Depends on**: Phase 24 (backend parsing and mapping APIs must exist)
**Requirements**: IMP-03, IMP-04, IMP-06, IMP-07, IMP-10
**Success Criteria** (what must be TRUE):
  1. User can select the import type (Contacts, Donations, Pledges) for their uploaded Smartsheet file
  2. User sees dropdown selects for each source column to map it to a CRM field, with auto-detected suggestions pre-filled
  3. Each auto-detected mapping shows a color-coded confidence indicator (green/yellow/red)
  4. User can preview the first 10 rows of mapped data before committing the import
  5. User can save a column mapping as a named template and reuse it for future imports of similar files
**Plans**: TBD

Plans:
- [ ] 25-01: TBD
- [ ] 25-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 20 -> 21 -> 22 -> 23 -> 24 -> 25

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
| 20. Security & Performance Fixes | v1.3 | 3/3 | Complete | 2026-02-17 |
| 21. Dark Mode & UI Polish | v1.3 | 3/3 | Complete | 2026-02-17 |
| 22. Filter Infrastructure | v1.3 | 3/3 | Complete | 2026-02-17 |
| 23. Per-Page Filter Implementation | v1.3 | Complete    | 2026-02-18 | - |
| 24. Smartsheet Import Backend | v1.3 | 0/? | Not started | - |
| 25. Smartsheet Import Frontend | v1.3 | 0/? | Not started | - |

---

*Last updated: 2026-02-17 (Phase 22 planned)*
