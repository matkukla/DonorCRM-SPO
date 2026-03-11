# DonorCRM Milestones

## v2.2 -- UI Polish, Journal Report & Supervisor Role
**Completed:** 2026-03-11
**Duration:** 57 days (2026-01-13 → 2026-03-10)

Delivered a comprehensive UI polish pass, rebuilt journal reporting, added Begin Prayer flow, introduced Mission Supervisor and Coach roles with scoped visibility and M2M assignments, built SPO import pipeline, fixed org contact data mapping, and closed all audit gaps.

**Scope:**
- 36 requirements implemented
- 10 phases executed (38-47)
- 34 plans completed
- 296 files changed, +34,664 / -1,951 lines

**Key Features:**
- UI polish: centered dialogs, "Potential Donor" rename, gift list Type column, cleaned analytics dashboard (removed Review Queue and heatmap)
- Dashboard modifications: chart toggle (bar/line), cross-section drag-and-drop, tightened gaps, removed stale text and tiles
- Journal report rebuilt: metrics cards, goal progress bar, Contacts by Stage and Decision Status charts, conditional alerts; single-click stage checkbox auto-creates stage event
- Begin Prayer: dedicated "Begin Prayer" button launching expanded Focus Mode with intention selection dialog
- Mission Supervisor role: scoped visibility, admin assignment management, missionary dashboard selector; later upgraded to M2M (multiple supervisors/coaches per missionary)
- Roles Redesign: staff→missionary, mission_supervisor→supervisor, Coach role with financial data block, Admin Assignments page, My Team page
- SPO import pipeline: MissionaryAlias name matching, gift attribution, prayer extraction, tri-source comparison (CLI/API)
- Org contact data mapping: organization_name displayed across list, search, CSV export, contact detail, and create/edit form
- Coach role gaps closed: IsStaffOrAbove allows coach safe-method access, coached_user_ids M2M persisted, stale role='staff' strings fixed

**Archives:**
- [v2.2-ROADMAP.md](milestones/v2.2-ROADMAP.md)
- [v2.2-REQUIREMENTS.md](milestones/v2.2-REQUIREMENTS.md)
- [v2.2-MILESTONE-AUDIT.md](milestones/v2.2-MILESTONE-AUDIT.md)

**Git Tag:** v2.2

---

## Completed Milestones

### v1.0 -- Journal Feature
**Completed:** 2026-01-29
**Duration:** 5 days (2026-01-24 -> 2026-01-29)

A fundraising campaign pipeline tracker enabling missionaries to manage donor relationships through a 6-stage pipeline.

**Scope:**
- 19 requirements implemented
- 6 phases executed (1-6)
- 24 plans completed
- 35 UAT tests passed

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

**Archives:**
- [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)
- [v1-MILESTONE-AUDIT.md](v1-MILESTONE-AUDIT.md)

**Git Tag:** v1.0

---

### v1.1 -- CSV Import
**Completed:** 2026-02-04
**Duration:** 5 days (2026-01-30 -> 2026-02-04)

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

### v1.2 -- Admin Analytics Dashboard
**Completed:** 2026-02-16
**Duration:** 4 days (2026-02-12 -> 2026-02-16)

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

### v1.3 -- Smartsheet Import, Filters & Polish
**Completed:** 2026-02-19
**Duration:** 3 days (2026-02-17 -> 2026-02-19)

Enable Smartsheet file import with column mapping, add comprehensive filtering across all list pages, and fix security/quality/dark mode issues.

**Scope:**
- 35 requirements implemented
- 7 phases executed (20-26)
- 20 plans completed, 37 tasks
- 166 files changed, +17,607 / -831 lines

**Key Features:**
- Security & performance: closed permission bypasses (owner-scoped querysets), fixed N+1 queries (400->3), file size limits, route guards with redirect+toast
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

### v2.0 -- Import Revamp, Prayer Intentions & Dashboard Polish
**Completed:** 2026-02-25
**Duration:** 5 days (2026-02-20 -> 2026-02-25)

Replace the existing Donation/Pledge system with Gift/RecurringGift models, build a Raiser's Edge CSV import pipeline, add prayer intentions tracking, and make dashboard tiles draggable.

**Scope:**
- 46 requirements implemented
- 10 phases executed (27-36)
- 27 plans completed

**Key Features:**
- Gift/RecurringGift models replacing Donation/Pledge (full data migration)
- Raiser's Edge CSV import pipeline (4 types: Constituent, Solicitor, Gift, Recurring Gift)
- Generic CSV import (contacts, donations) with configurable matching
- Solicitor model with auto-linking and credit splitting
- Prayer Intentions with Focus Mode, Today's Focus, contact integration
- Draggable dashboard tiles (dnd-kit)
- Full-stack audit: 52 issues fixed (security, performance, code quality, UI/UX)

**Archives:**
- [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)
- [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)
- [v2.0-MILESTONE-AUDIT.md](milestones/v2.0-MILESTONE-AUDIT.md)

**Git Tag:** v2.0

---

### v2.1 -- Security Hardening
**Completed:** 2026-02-25

Harden DonorCRM against common security vulnerabilities identified in Phase 36's full-stack audit.

**Scope:**
- 1 phase executed (37)
- 3 plans completed, 6 tasks
- 20 files changed, +845 lines

**Key Features:**
- Auth rate limiting (5/min via DRF ScopedRateThrottle) on login and token refresh
- Fixed broken refresh token rotation in frontend (both tokens stored after refresh)
- Custom password validator requiring letters + numbers
- Content-Security-Policy via django-csp in production
- Referrer-Policy and Permissions-Policy on frontend static site
- API docs gated behind authentication in production
- 8 Python CVEs patched (Django 4.2.28, gunicorn 22.x)
- 3 JS CVEs patched (axios, minimatch, ajv)
- Comprehensive SECURITY-REPORT.md with 12 findings documented

**Archives:**
- [v2.1-ROADMAP.md](milestones/v2.1-ROADMAP.md)

**Git Tag:** v2.1

---

## Active Milestones

_No active milestones. Run `/gsd:new-milestone` to start the next one._

---

*Last updated: 2026-03-11 (v2.2 shipped)*

