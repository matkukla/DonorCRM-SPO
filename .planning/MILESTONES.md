# DonorCRM Milestones

## Completed Milestones

### v1.0 — Journal Feature
**Completed:** 2026-01-29
**Duration:** 5 days (2026-01-24 → 2026-01-29)

A fundraising campaign pipeline tracker enabling missionaries to manage donor relationships through a 6-stage pipeline.

**Scope:**
- 19 requirements implemented
- 6 phases executed (1-6)
- 24 plans completed
- 35 UAT tests passed

**Key Features:**
- Journal CRUD with owner-scoped visibility
- Contact membership management (many-to-many)
- 6-stage pipeline: Contact → Meet → Close → Decision → Thank → Next Steps
- Decision tracking with history (dual-table pattern)
- Interactive grid UI with stage cell indicators
- Event timeline drawer with infinite scroll
- Analytics charts (decision trends, stage activity, pipeline breakdown)
- Contact detail integration (Journals tab)
- Task system integration (journal-linked tasks)
- Admin analytics endpoints

**Archives:**
- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
- [v1-MILESTONE-AUDIT.md](v1-MILESTONE-AUDIT.md)

**Git Tag:** v1.0

---

### v1.1 — CSV Import
**Completed:** 2026-02-04
**Duration:** 5 days (2026-01-30 → 2026-02-04)

Enable admins to import SPO-exported CSV files (Funds, Entities, Transactions, Pledges) into DonorCRM with validation, preview, and idempotent upserts.

**Scope:**
- 19 requirements implemented
- 6 phases executed (7-12)
- 15 plans completed

**Key Features:**
- Import Center UI for 4 CSV types
- Fund model for account/campaign tracking
- External ID support for idempotent imports
- Row-level validation and error reporting
- Import audit trail (ImportRun, ImportRowError)

**Archives:**
- [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)
- [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)

**Git Tag:** v1.1

---

### v1.2 — Admin Analytics Dashboard
**Completed:** 2026-02-16
**Duration:** 4 days (2026-02-12 → 2026-02-16)

Cross-missionary visibility into fundraising activity, pipeline health, and stalled contacts for coaches and leadership.

**Scope:**
- 26 requirements implemented
- 7 phases executed (13-19)
- 18 plans completed, 65 tasks
- 84 commits, 42 files changed, +6,605 lines

**Key Features:**
- Dashboard Overview with summary cards, trend charts, conversion funnel, team activity, and coaching alerts
- Stalled Contacts monitoring (14+ day detection) with pagination and sorting
- Per-missionary User Detail pages with individual trend charts and journal listings
- Interactive drill-down: clickable funnel segments and user quick-view slide-in panels
- Date range filtering with presets, CSV exports for stalled contacts and team activity
- Activity heatmap calendar, time period comparison with trend arrows, user comparison

**Archives:**
- [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md)
- [v1.2-REQUIREMENTS.md](milestones/v1.2-REQUIREMENTS.md)
- [v1.2-MILESTONE-AUDIT.md](milestones/v1.2-MILESTONE-AUDIT.md)

**Git Tag:** v1.2

---

### v1.3 — Smartsheet Import, Filters & Polish
**Completed:** 2026-02-19
**Duration:** 3 days (2026-02-17 → 2026-02-19)

Enable Smartsheet file import with column mapping, add comprehensive filtering across all list pages, and fix security/quality/dark mode issues.

**Scope:**
- 35 requirements implemented
- 7 phases executed (20-26)
- 20 plans completed, 37 tasks
- 166 files changed, +17,607 / -831 lines

**Key Features:**
- Security & performance: closed permission bypasses (owner-scoped querysets), fixed N+1 queries (400→3), file size limits, route guards with redirect+toast
- Dark mode & quality: fixed 50+ hardcoded colors across 12 files, Error Boundary, CSV formula sanitization, donation edit stats fix
- Filter infrastructure: reusable server-side filter system (django-filter 24.3, nuqs URL persistence, presets, badges, clear-all, filtered CSV export)
- Per-page filters: applied to all 5 list pages (contacts, donations, pledges, journals, transactions) with admin owner dropdowns
- Smartsheet MPD import: end-to-end file upload with magic-byte format detection, name matching, financial snapshot storage, dashboard and missionary views
- Contact owner filter: admin owner dropdown on ContactList closing FLT-04 gap

**Archives:**
- [v1.3-ROADMAP.md](milestones/v1.3-ROADMAP.md)
- [v1.3-REQUIREMENTS.md](milestones/v1.3-REQUIREMENTS.md)
- [v1.3-MILESTONE-AUDIT.md](milestones/v1.3-MILESTONE-AUDIT.md)

**Git Tag:** v1.3

---

## Planned Milestones

### v2.0 — Future Enhancements (Not Started)

Planned requirements from v1 deferral:
- JRN-V2-02: Real-Time Collaboration
- JRN-V2-03: Communication Integration
- JRN-V2-04: Mobile Native App
- JRN-V2-05: Bulk Journal Operations
- JRN-V2-06: Custom Stage Definitions
- JRN-V2-07: AI Suggestions
- Configurable alert thresholds (per coach)
- Email digest reports for coaches

---

*Last updated: 2026-02-19 (v1.3 milestone completed)*
