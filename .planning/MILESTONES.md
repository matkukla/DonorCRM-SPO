# DonorCRM Milestones

## v1.0 Duplicate Contact Checking + Merging (Shipped: 2026-03-28)

**Phases completed:** 2 phases, 8 plans, 13 tasks

**Key accomplishments:**

- pg_trgm-powered duplicate detection with 3-tier confidence scoring and atomic contact merge handling all 6 FK relationship types including JournalContact conflict resolution
- 4 DRF APIView endpoints for duplicate check/scan/merge/dismiss with serializers, merged-contact list filtering, and 9 passing API integration tests
- Shadcn RadioGroup/AlertDialog components, duplicate detection API types and functions, React Query hooks with cache invalidation, and vitest infrastructure with 4 passing behavioral tests
- DuplicateList page with scan/dismiss/review actions, ConfidenceBadge component, sidebar navigation, and route registration for duplicate contact management
- Side-by-side contact merge page with survivor selection, 15-field comparison including external IDs, related records summary, and AlertDialog confirmation
- DuplicateWarningDialog component with ConfidenceBadge, ContactForm pre-save duplicate check integration, and 9 passing vitest behavioral tests
- Models follow codebase conventions:
- One-liner:

---

## v2.3 Goal Tracking & View As (Shipped: 2026-03-25)

**Phases completed:** 8 phases, 30 plans, 52 tasks

**Key accomplishments:**

- Exposed MPDSnapshot.monthly_average through /mpd/me/ and /mpd/overview/ endpoints with 4 TDD-driven tests confirming correct string serialization and null handling
- Monthly Average tile added as first of 4 MPD cards for all users, plus admin-only MPD Overview table with Monthly Average column, hidden during View As browsing
- 17 failing pytest stubs across 3 test files covering fiscal year utilities, goal progress service, and goals API endpoint — all fail for the right reason (missing modules/endpoints)
- Pure-Python fiscal year utility (fiscal_year_start/end/months_remaining) and extracted SQL gift aggregation helper (_monthly_equivalent_aggregate) in apps/core/, unblocking Plan 03 migrations and Plan 04 goal service.
- Django two-migration schema change: DecimalField monthly_goal renamed to PositiveBigIntegerField monthly_support_goal_cents, goal_weeks added, GoalJournalSelection model created with user/journal FK unique_together
- Django REST API for GET/PATCH /api/v1/goals/me/ backed by get_goal_progress() service computing recurring + one-time fiscal-year gift totals from journal-scoped contacts
- Extended get_goal_progress() to return calls_count and meetings_count from JournalStageEvent records, enabling the frontend Goal page to display read-only activity progress bars.
- Custom div-based progress bar with four milestone tick marks (25/50/75/100%), dynamic color coding for Monthly Support tracking, and disabled state — standalone, ready for GoalPage.tsx to import
- Typed goals.ts API module + useGoal.ts React Query hooks wiring GET/PATCH /api/v1/goals/me/ with direct cache update on mutation
- Complete Goal page with Goal Settings card, read-only Progress bars from server event counts, Partners-formula pacing tiles, and supervisor/admin read-only enforcement wired to live API data
- pytest scaffold with 6 role-behavior unit tests for get_visible_user_ids() in correct RED state: admin and supervisor fail asserting {own_id} while finance/read_only/coach/missionary pass
- get_visible_user_ids() updated so admin and supervisor return {user.id} — cascades automatically to all 13 caller views, restricting both roles to own-data-only by default
- Role guard added to _resolve_target_user() so admin/supervisor can select any missionary via dashboard dropdown without 403, while get_visible_user_ids() default scoping remains intact
- 20 pytest-django RED tests covering ViewAsMiddleware mutation blocking, permission validation, ViewableUsersView endpoint, and get_visible_user_ids view_as scoping override
- ViewAsMiddleware blocking POST/PUT/PATCH/DELETE with 403 and validating admin/supervisor-only header access, registered in Django MIDDLEWARE after AuthenticationMiddleware
- 1. [Rule 2 - Missing functionality] prayers/views.py — _owner_scoped_queryset helper
- GET /api/v1/users/viewable/ endpoint returning [{id, full_name}] for admin (all active missionaries) and supervisor (assigned missionaries only), with 403 for missionary role
- One-liner:
- Amber ViewAsBanner in AppLayout and Dashboard picker wired to ViewAsContext — admin/supervisor can enter/exit View As from Dashboard, banner persists across all pages
- [Rule 2 - Missing mutation guard] PrayerList inline status Select
- Seven-stage PipelineStage enum with SCHEDULED between CONTACT and MEET, serializer metadata validation for scheduled_date, and summary enrichment for grid display
- CalendarDays icon rendering, dialog-open click behavior, and 7-column grid layout for scheduled pipeline stage
- LogEventDialog with Calendar date picker and time input for scheduled stage, user-friendly metadata display in EventTimelineDrawer, and scheduled stage in ReportCharts analytics configs
- BroadcastTask model with 4-target resolution, atomic bulk distribution, cascade edit, and cancel with completed-copy preservation
- Broadcast task CRUD endpoints with role-based access, cascade edit/cancel, TaskSerializer extension, and 27-test coverage
- Broadcast API client with 6 typed functions and 6 React Query hooks with cross-key cache invalidation for broadcasts, tasks, and dashboard
- BroadcastTaskDialog with form/confirmation steps, TaskList broadcast badge and button, TaskDetail broadcast info bar with missionary action restrictions
- Admin BroadcastList and BroadcastDetail pages with DataTable completion tracking, supervisor TeamPage broadcast section, sidebar navigation, and route registration

---

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
