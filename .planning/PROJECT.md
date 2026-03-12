# DonorCRM

## What This Is

A donor relationship management system for missionaries. Includes contact management (including org-type contacts), gift tracking (with solicitor credit splitting), recurring gift management, task system, Journal feature for fundraising campaign pipelines, Raiser's Edge/SPO/generic CSV import, Smartsheet MPD report import, prayer intentions tracking with Begin Prayer flow, comprehensive list page filtering with URL-based state, draggable dashboard tiles, and an Admin Analytics Dashboard. Supports a full role hierarchy: missionary, supervisor (scoped to assigned missionaries), coach (contacts + journals only), and admin — all with M2M assignment support.

## Core Value

Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## Current Milestone: v2.3 Goal Tracking & View As

**Goal:** Give missionaries a dedicated Goal page to track fundraising progress, and give supervisors/admins a View As mode to see any missionary's data in read-only.

**Target features:**
- Goal page with fiscal-year progress calculation, journal selection, pacing targets, and progress bars
- Supervisor/admin View As mode with persistent banner, read-only enforcement, and `X-View-As-User-Id` backend middleware
- Default data scoping — admins/supervisors see only their own data unless in View As mode
- Fiscal year configuration (July 1 start) as shared utility
- MPD dashboard enhancements: Monthly Average tile + Admin MPD Overview section

## Current State (after v2.2)

- **Backend:** Django 4.2.28 + DRF, ~26,000 LOC Python (excluding migrations), 9 apps (contacts, gifts, prayers, tasks, journals, insights, users, imports, core)
- **Frontend:** React 19 + TypeScript + Vite, ~26,000 LOC TypeScript
- **Database:** PostgreSQL with Django ORM, UUID primary keys
- **UI:** Tailwind CSS + Radix UI components, Recharts for charts, @dnd-kit for drag-and-drop, TanStack Table for sorting (heatmap removed in v2.2)
- **Filtering:** django-filter 24.3 backend, nuqs URL state frontend, FilterBar shared component
- **Import systems:** Raiser's Edge CSV (4 types), Generic CSV (contacts, donations), Smartsheet MPD (Excel/CSV), SPO import pipeline (missionaries, gifts, prayers)
- **Security:** Rate-limited auth (20/min demo mode), CSP headers (django-csp), authenticated API docs, security-scanned dependencies
- **Roles:** missionary, supervisor (M2M scoped visibility), coach (M2M, contacts+journals only), admin — get_visible_user_ids() centralized helper
- **Total milestones shipped:** 7 (v1.0, v1.1, v1.2, v1.3, v2.0, v2.1, v2.2)
- **Total plans executed:** 141 across 47 phases

### What's New in v2.2

- UI polish: centered dialogs system-wide, "Potential Donor" rename, gift list Type column, analytics Review Queue and heatmap removed
- Dashboard: bar/line chart toggle, cross-section drag-and-drop, tightened tile gaps, stale text removed
- Journal report rebuilt: 4 metric cards, goal progress bar, Contacts by Stage and Decision Status charts, conditional alerts
- Journal grid: single-click stage checkbox auto-creates event; Decision column between Close and Thank
- Begin Prayer: dedicated "Begin Prayer" button launching expanded Focus Mode with intention selection dialog
- Mission Supervisor role with scoped visibility → upgraded to M2M (multiple supervisors and coaches per missionary)
- Roles Redesign: staff→missionary, mission_supervisor→supervisor, Coach role with financial data block
- Admin Assignments page with multi-select chips and view toggle; My Team page with missionary profiles
- SPO import pipeline: MissionaryAlias name matching, gift attribution, prayer extraction (CLI/API)
- Org contact data mapping: organization_name across list, search, CSV export, contact detail, create/edit form
- Coach role gaps closed: IsStaffOrAbove allows coach safe-method access, coached_user_ids M2M persisted

## Requirements

### Validated

<details>
<summary>v1.0-v1.3 requirements (68 items)</summary>

- ✓ Contact management (CRUD, ownership, search, filtering) — existing
- ✓ Donation tracking with automatic contact stat updates — existing
- ✓ Pledge management with status transitions and fulfillment — existing
- ✓ Task system with due dates, status, and contact association — existing
- ✓ Event/notification system for audit trail — existing
- ✓ JWT authentication with role-based access control — existing
- ✓ Dashboard with aggregated views and reporting — existing
- ✓ CSV import/export for contacts and donations — existing
- ✓ Group/tag system for contact segmentation — existing
- ✓ Journal CRUD with owner-scoped visibility — v1.0
- ✓ Contact membership management (many-to-many) — v1.0
- ✓ 6-stage pipeline with event logging — v1.0
- ✓ Decision tracking with history (dual-table pattern) — v1.0
- ✓ Interactive grid UI with stage cell indicators — v1.0
- ✓ Analytics charts (decision trends, stage activity, pipeline breakdown) — v1.0
- ✓ Contact detail integration (Journals tab) — v1.0
- ✓ Task system integration (journal-linked tasks) — v1.0
- ✓ Admin analytics endpoints — v1.0
- ✓ Fund model for account/campaign tracking — v1.1
- ✓ External ID fields for idempotent imports — v1.1
- ✓ Import audit trail (ImportRun, ImportRowError) — v1.1
- ✓ 4-type CSV import pipeline (Funds, Entities, Transactions, Pledges) — v1.1
- ✓ Import Center UI with upload/preview/validate/import workflow — v1.1
- ✓ Error CSV download and row-level validation reporting — v1.1
- ✓ Dashboard Overview with summary cards, trend charts, conversion funnel, team activity, alerts — v1.2
- ✓ Stalled Contacts page (14+ days no activity) with pagination/sorting — v1.2
- ✓ User Detail page with per-missionary performance and journal listings — v1.2
- ✓ User Drilldown panel (slide-in sidebar) — v1.2
- ✓ Drill-down charts (click funnel/chart to see underlying contacts) — v1.2
- ✓ Time period and user comparison modes — v1.2
- ✓ Activity heatmap calendar view — v1.2
- ✓ 13 API endpoints with ADMIN role-based visibility — v1.2
- ✓ Date range filtering and CSV export — v1.2
- ✓ Pace calculation and stalled detection business logic — v1.2
- ✓ Permission bypass fixes (owner-scoped querysets on all ListAPIViews) — v1.3
- ✓ N+1 query fix in journal grid (400→3 queries with prefetch) — v1.3
- ✓ File size limits on upload endpoints (10 MB) — v1.3
- ✓ Frontend route guards with redirect + toast for non-admin users — v1.3
- ✓ Dark mode color audit (50+ hardcoded colors fixed across 12 files) — v1.3
- ✓ WCAG 4.5:1 contrast compliance in dark mode — v1.3
- ✓ React Error Boundary with fallback UI — v1.3
- ✓ CSV formula sanitization on all export endpoints — v1.3
- ✓ Donation edit stats refresh fix — v1.3
- ✓ Decimal arithmetic for pledge monthly_equivalent — v1.3
- ✓ Dashboard GET side-effect decoupling (mark-as-seen → POST) — v1.3
- ✓ Reusable server-side filter system (django-filter 24.3 + nuqs URL state) — v1.3
- ✓ Filter presets, badges, clear-all, filtered CSV export on all list pages — v1.3
- ✓ Per-page filters: contacts, donations, pledges, journals, transactions — v1.3
- ✓ Admin owner filter dropdowns on contacts and donations — v1.3
- ✓ Smartsheet MPD report upload (Excel/CSV with magic-byte format detection) — v1.3
- ✓ Missionary name matching with unmatched row reporting — v1.3
- ✓ MPD financial snapshot storage with historical accumulation — v1.3
- ✓ MPD data on admin dashboard and missionary personal views — v1.3

</details>

- ✓ Gift model replacing Donation with solicitor credit support and cents-based amounts — v2.0
- ✓ RecurringGift model replacing Pledge with installment fields and status tracking — v2.0
- ✓ Solicitor model with normalized name matching and User auto-linking — v2.0
- ✓ ImportBatch model with SHA256 file deduplication — v2.0
- ✓ PrayerIntention model with contact FK and status tracking — v2.0
- ✓ RE CSV import pipeline (4 types) with encoding detection and row-level errors — v2.0
- ✓ Generic CSV import for contacts and donations with configurable matching — v2.0
- ✓ Data migration: Donation→Gift, Pledge→RecurringGift with UUID preservation — v2.0
- ✓ Gift/RecurringGift UI with solicitor credits and expanded filters — v2.0
- ✓ Unified Import/Export page with RE tabs, generic import, and history — v2.0
- ✓ Prayer Intentions page with Focus Mode and contact integration — v2.0
- ✓ Draggable dashboard tiles with dnd-kit — v2.0
- ✓ Full-stack audit (security, performance, code quality, UI/UX, API consistency) — v2.0
- ✓ Auth endpoint rate limiting (ScopedRateThrottle, 5/min production) — v2.1
- ✓ Refresh token rotation fix (both tokens stored after refresh) — v2.1
- ✓ Custom password validator (letters + numbers required) — v2.1
- ✓ Content-Security-Policy via django-csp in production — v2.1
- ✓ Security headers on frontend static site (CSP, Referrer-Policy, Permissions-Policy) — v2.1
- ✓ API docs authentication gate in production — v2.1
- ✓ Python dependency CVE patches (Django 4.2.28, gunicorn 22.x) — v2.1
- ✓ JS dependency CVE patches (axios, minimatch, ajv) — v2.1
- ✓ Security audit report (SECURITY-REPORT.md) — v2.1
- ✓ UI polish: centered dialogs, "Potential Donor" rename, gift Type column, analytics cleanup — v2.2
- ✓ Dashboard chart toggle, cross-section drag-and-drop, tightened gaps, stale tiles removed — v2.2
- ✓ Journal report rebuilt with metrics cards, charts, alerts; single-click stage checkbox — v2.2
- ✓ Begin Prayer flow with intention selection dialog and expanded Focus Mode — v2.2
- ✓ Mission Supervisor role with scoped visibility and M2M assignment (multiple supervisors/coaches) — v2.2
- ✓ Roles Redesign: missionary/supervisor/coach roles with Coach financial block — v2.2
- ✓ Admin Assignments page + My Team page with missionary profiles — v2.2
- ✓ SPO import pipeline (MissionaryAlias, gift attribution, prayer extraction) — v2.2
- ✓ Org contact data mapping: organization_name across all views and export — v2.2
- ✓ Coach role gaps: IsStaffOrAbove fix, coached_user_ids M2M, stale role strings fixed — v2.2

### Active

- [ ] Goal page: fiscal-year support calculation from selected journals
- [ ] Goal page: journal selection persisted per user
- [ ] Goal page: pacing targets (calls/meetings based on goal)
- [ ] Goal page: three progress bars (support $, calls, meetings) with milestone markers
- [ ] Goal page: read-only mode for supervisors/admins
- [ ] Goal page: navigation item in sidebar (below Dashboard)
- [ ] Goal fields: monthly_support_goal_cents on User model; GoalJournalSelection model
- [ ] Fiscal year utility: July 1 start, months remaining calculation (shared backend + frontend)
- [ ] View As mode: X-View-As-User-Id middleware with permission check
- [ ] View As mode: GET /api/users/viewable endpoint
- [ ] View As mode: frontend ViewAsContext + API header injection
- [ ] View As mode: persistent banner with Exit button
- [ ] View As mode: read-only enforcement (mutations blocked frontend + backend)
- [ ] Data scoping: all roles (incl. admin) default to owner=self; View As unlocks another user
- [ ] MPD dashboard: Monthly Average tile in MPD Financial Overview section
- [ ] MPD dashboard: Admin MPD Overview section visible to admin role

### Out of Scope

- Real-time updates via WebSocket/SSE — polling sufficient for dashboard
- Email digest reports — no email infrastructure yet
- Performance scoring/gamification — could demotivate missionaries
- Configurable alert thresholds (per coach) — requires user preferences model
- Goal setting & tracking UI — requires new Goal model
- Saved filter views — URL params already bookmarkable and shareable
- Mobile-optimized activity logging — web responsive sufficient
- Audit log for compliance — defer to future
- Custom stage definitions — fixed 6-stage pipeline
- AI-generated suggestions — manual workflow only
- Import undo/rollback — snapshots are immutable; admin can re-upload corrected files
- Automated Smartsheet API — manual monthly upload sufficient
- Advanced filter query builder — stacked AND covers 95% of use cases
- Dashboard tile persistence (backend) — session-only sufficient for now
- Prayer intention reminders/notifications — no notification infrastructure

## Context

### Domain Context
- Primary user: individual missionary fundraiser
- Secondary user: coach/supervisor monitoring 5-15 missionaries
- Workflow: identify prospects → contact → meet → ask → track decision → thank → plan next
- A "journal" represents a fundraising campaign/push (e.g., "Spring 2026 Support Raising")
- Missionaries track multiple donors through the pipeline simultaneously
- Decision tracking is critical: amount pledged, cadence, and status changes over time
- Organization leadership and coaches (10-20 people) use analytics dashboard for cross-missionary visibility
- Monthly Smartsheet MPD report tracks each missionary's fundraising financial health

### Data Model Decisions
- Money stored in cents (PositiveBigIntegerField) with Decimal amount_dollars property
- Gift/RecurringGift models with solicitor credit splitting (GiftCredit/RecurringGiftCredit junction tables)
- Decision has "current" table (unique per journal+contact) and "history" table
- Stage events are append-only log entries, not state transitions
- Next Steps are independent checklist items, not single boolean
- Journal tasks link to existing Task model via journal_id foreign key
- MPD financial fields use DecimalField (max_digits=12) for values like $71,352.72
- MPDSnapshot accumulates per user per upload (no overwrite)
- PrayerIntention uses M2M to gifts (multi-gift prayer dedup)

## Constraints

- **Tech stack**: Django/DRF backend, React/TypeScript frontend — follow existing patterns
- **Data model**: Use cents for money, UUID PKs, TimeStampedModel base class
- **Access control**: Owner-scoped with admin visibility — follow existing permission patterns
- **UI framework**: Tailwind CSS + Radix UI primitives — match existing component library
- **Charts**: Recharts for standard charts, @uiw/react-heat-map for heatmap
- **Performance**: Report queries must avoid N+1; use select_related/prefetch_related and aggregation
- **Filtering**: Use django-filter 24.3 (NOT 25.2), nuqs for URL state, FilterBar for UI
- **Dark mode**: All new UI must include dark: variants; use semantic Tailwind tokens
- **Code splitting**: Heavy pages use React.lazy; large vendors in dedicated Vite chunks

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django/DRF over Node/Prisma | Follow existing codebase patterns | ✓ Good |
| Link journal tasks to existing Task model | Avoid duplicate task systems, reuse existing UI | ✓ Good |
| Owner + admin visibility for journals | Supports cross-missionary analytics | ✓ Good |
| Fixed 6-stage pipeline | Matches missionary fundraising workflow | ✓ Good |
| Cents for money storage | Precision, no floating point issues | ✓ Good |
| Database-level aggregation (v1.2) | <20 queries per endpoint, avoids N+1 | ✓ Good |
| DRF permission classes over manual checks (v1.2) | Consistent enforcement, prevents ListAPIView bypass | ✓ Good |
| django-filter 24.3 pinned (v1.3) | 25.2 requires Django 5.2+; individual DateFilters avoid suffix | ✓ Good |
| nuqs for URL filter state (v1.3) | Type-safe parsers, shallow:false triggers React Query re-renders | ✓ Good |
| Magic-byte format detection for MPD upload (v1.3) | No file extension check; handles XLSX and CSV reliably | ✓ Good |
| REPLACE Donation/Pledge with Gift/RecurringGift (v2.0) | Full migration, not dual-model — cleaner long-term | ✓ Good |
| Solicitor.user as ForeignKey not OneToOne (v2.0) | Many-to-one allows multiple solicitor records per user | ✓ Good |
| PrayerIntention.gifts as M2M (v2.0) | Multi-gift prayer dedup without duplicate intentions | ✓ Good |
| Old SPO import removed with 410 Gone (v2.0) | RE pipeline supersedes; clean break | ✓ Good |
| Desktop-only drag for dashboard (v2.0) | PointerSensor only per user decision | ✓ Good |
| Configurable match_by for generic import (v2.0) | Supports name, email, external_id matching strategies | ✓ Good |
| React.lazy code splitting for 12 pages (v2.0) | Reduces initial bundle, improves first load | ✓ Good |
| ScopedRateThrottle for auth endpoints (v2.1) | Per-endpoint control via throttle_scope, 100/min dev override | ✓ Good |
| Strict CSP (default-src: 'none') for Django API (v2.1) | API serves JSON only; admin/docs excluded from CSP | ✓ Good |
| Conditional API docs auth via settings.DEBUG (v2.1) | Open in dev for convenience, gated in production | ✓ Good |
| django-csp 4.0 dict config format (v2.1) | CONTENT_SECURITY_POLICY dict with EXCLUDE_URL_PREFIXES | ✓ Good |
| Dialog-first modal pattern (v2.2) | All overlays use centered Dialog with max-h-[80vh] and overflow-y-auto; no side-sliding Sheets | ✓ Good |
| Single-click stage checkbox auto-creates event (v2.2) | Removed transition warning toasts for independent stage toggles per JRNL-08 | ✓ Good |
| get_visible_user_ids() centralized visibility helper (v2.2) | Returns None for all-access roles, set of IDs for scoped roles — clean pattern for all views | ✓ Good |
| Supervisor/coach as M2M not FK (v2.2 Phase 46) | Supports multiple supervisors/coaches per missionary; FK data preserved in migration | ✓ Good |
| IsSupervisorWriteRestricted + IsStaffOrAbove permission classes (v2.2) | Separate permission classes for write restriction vs role gate; coach gets safe-method access | ✓ Good |
| SPO import as CLI/API only — no frontend UI (v2.2) | Pre-existing deferred decision; CLI workflow is intentional for admin-only operation | — Pending |
| staff_users() in managers.py uses stale role='staff' (v2.2 tech debt) | Method appears unused in production; accepted as low-priority tech debt | ⚠️ Revisit |

---
*Last updated: 2026-03-12 after v2.3 milestone started*
