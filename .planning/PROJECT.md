# DonorCRM

## What This Is

A donor relationship management system for missionaries. Includes contact management, gift tracking (with solicitor credit splitting), recurring gift management, task system, Journal feature for fundraising campaign pipelines, Raiser's Edge and generic CSV import, Smartsheet MPD report import, prayer intentions tracking, comprehensive list page filtering with URL-based state, draggable dashboard tiles, and an Admin Analytics Dashboard for coaches and leadership to monitor missionary performance across the organization.

## Core Value

Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## Current State (after v2.1)

- **Backend:** Django 4.2.28 + DRF, ~26,000 LOC Python (excluding migrations), 9 apps (contacts, gifts, prayers, tasks, journals, insights, users, imports, core)
- **Frontend:** React 19 + TypeScript + Vite, ~24,000 LOC TypeScript
- **Database:** PostgreSQL with Django ORM, UUID primary keys
- **UI:** Tailwind CSS + Radix UI components, Recharts for charts, @uiw/react-heat-map for heatmap, @dnd-kit for drag-and-drop, TanStack Table for sorting
- **Filtering:** django-filter 24.3 backend, nuqs URL state frontend, FilterBar shared component
- **Import systems:** Raiser's Edge CSV (4 types), Generic CSV (contacts, donations), Smartsheet MPD (Excel/CSV)
- **Security:** Rate-limited auth (5/min), CSP headers (django-csp), authenticated API docs, security-scanned dependencies
- **Total milestones shipped:** 6 (v1.0, v1.1, v1.2, v1.3, v2.0, v2.1)
- **Total plans executed:** 107 across 37 phases

### What's New in v2.1

- Auth rate limiting (5/min) via DRF ScopedRateThrottle on login and token refresh
- Fixed refresh token rotation (frontend stores both access + refresh tokens)
- Custom AlphanumericPasswordValidator (requires letters + numbers)
- Content-Security-Policy via django-csp in production
- Referrer-Policy and Permissions-Policy on frontend static site
- API docs (schema/swagger/redoc) gated behind authentication in production
- 8 Python CVEs + 3 JS CVEs patched
- bandit and pip-audit added as dev dependencies for CI security scanning

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

### Active

_No active milestone. Run `/gsd:new-milestone` to start the next one._

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

---
*Last updated: 2026-02-25 after v2.1 shipped*
