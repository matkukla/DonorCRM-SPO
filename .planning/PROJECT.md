# DonorCRM

## What This Is

A donor relationship management system for missionaries. Includes contact management, donation tracking, pledge management, task system, Journal feature for fundraising campaign pipelines, SPO-compatible CSV import, Smartsheet MPD report import, comprehensive list page filtering with URL-based state, and an Admin Analytics Dashboard for coaches and leadership to monitor missionary performance across the organization.

## Core Value

Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems, and leadership can proactively support their teams through cross-missionary analytics.

## Requirements

### Validated

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

### Active

## Current Milestone: v2.0 — Import Revamp, Prayer Intentions & Dashboard Polish

**Goal:** Replace the existing import/donation/pledge system with a Raiser's Edge-compatible import pipeline, add prayer intentions tracking, and make dashboard tiles draggable.

**Target features:**
- Raiser's Edge CSV import (4 types: Constituent, Solicitor, Gift, Recurring Gift)
- Generic CSV import layer (contacts, donations)
- Gift/RecurringGift models replacing Donation/Pledge
- Solicitor model with auto-linking to User accounts
- SHA256-based import deduplication (ImportBatch)
- Gift credit splitting (one gift credits multiple missionaries)
- Data migration: existing Donations → Gifts, Pledges → RecurringGifts
- Prayer Intentions tied to contacts (with auto-creation from RE gift prayer descriptions)
- Draggable dashboard tiles (session-only, no persistence)
- UI rename: "Donations" → "Gifts", "Pledges" → "Recurring Gifts"
- Update all dependent features (dashboard, contact stats, list pages, filters, exports)

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
- Multi-select filter dropdowns — complicates serialization; marginal value

## Context

### Current State (after v1.3)
- **Backend:** Django 4.2 + DRF, ~25,000 LOC Python (excluding migrations), 8 apps
- **Frontend:** React 19 + TypeScript + Vite, ~23,000 LOC TypeScript, ~150 files
- **Database:** PostgreSQL with Django ORM, UUID primary keys
- **UI:** Tailwind CSS + Radix UI components, Recharts for charts, @uiw/react-heat-map for heatmap, TanStack Table for sorting
- **Filtering:** django-filter 24.3 backend, nuqs URL state frontend, FilterBar shared component
- **Import systems:** SPO CSV import (4 types) + Smartsheet MPD import (Excel/CSV)
- **Total milestones shipped:** 4 (v1.0, v1.1, v1.2, v1.3)
- **Total plans executed:** 77 across 26 phases

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
- Money stored in cents (integer) for precision
- Decision has "current" table (unique per journal+contact) and "history" table
- Stage events are append-only log entries, not state transitions
- Next Steps are independent checklist items, not single boolean
- Journal tasks link to existing Task model via journal_id foreign key
- MPD financial fields use DecimalField (max_digits=12) for values like $71,352.72
- MPDSnapshot accumulates per user per upload (no overwrite)

## Constraints

- **Tech stack**: Django/DRF backend, React/TypeScript frontend — follow existing patterns
- **Data model**: Use cents for money, UUID PKs, TimeStampedModel base class
- **Access control**: Owner-scoped with admin visibility — follow existing permission patterns
- **UI framework**: Tailwind CSS + Radix UI primitives — match existing component library
- **Charts**: Recharts for standard charts, @uiw/react-heat-map for heatmap
- **Performance**: Report queries must avoid N+1; use select_related/prefetch_related and aggregation
- **Compatibility**: New models must work with existing Contact, Task, User models
- **Filtering**: Use django-filter 24.3 (NOT 25.2), nuqs for URL state, FilterBar for UI
- **Dark mode**: All new UI must include dark: variants; use semantic Tailwind tokens

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django/DRF over Node/Prisma | Follow existing codebase patterns | ✓ Good |
| Link journal tasks to existing Task model | Avoid duplicate task systems, reuse existing UI | ✓ Good |
| Owner + admin visibility for journals | Supports cross-missionary analytics | ✓ Good |
| Contact "Journals" as new tab | Keep contact detail focused | ✓ Good |
| Fixed 6-stage pipeline | Matches missionary fundraising workflow | ✓ Good |
| Cents for money storage | Precision, no floating point issues | ✓ Good |
| Extend insights app for analytics (v1.2) | Reuse existing service pattern, avoid new app | ✓ Good |
| F() expressions for atomic updates (v1.2) | Prevents race conditions in concurrent writes | ✓ Good |
| Database-level aggregation (v1.2) | <20 queries per endpoint, avoids N+1 | ✓ Good |
| Subquery annotation for stalled detection (v1.2) | Efficient correlated query, includes zero-activity contacts | ✓ Good |
| DRF permission classes over manual checks (v1.2) | Consistent enforcement, prevents ListAPIView bypass | ✓ Good |
| StreamingHttpResponse for CSV export (v1.2) | Memory-efficient for large datasets | ✓ Good |
| Client-side sort for small tables, server-side for large (v1.2) | Right tool for dataset size | ✓ Good |
| URL param sync for date filters (v1.2) | Shareable dashboard URLs, browser back/forward works | ✓ Good |
| django-filter 24.3 pinned (v1.3) | 25.2 requires Django 5.2+; individual DateFilters avoid suffix breaking change | ✓ Good |
| nuqs for URL filter state (v1.3) | Type-safe parsers, shallow:false triggers React Query re-renders | ✓ Good |
| Owner filter in get_queryset not FilterSet (v1.3) | Security: admin-only, avoids exposing filter to non-admins | ✓ Good |
| OWASP single-quote prefix for CSV sanitization (v1.3) | Spreadsheet-native text-mode indicator, minimal disruption | ✓ Good |
| Magic-byte format detection for MPD upload (v1.3) | No file extension check needed; handles both XLSX and CSV reliably | ✓ Good |
| DecimalField for MPD financial data (v1.3) | Accurate representation of currency and percentage values | ✓ Good |
| Duplicate user names → unmatched (v1.3) | Ambiguous match is worse than no match; admin resolves manually | ✓ Good |

---
*Last updated: 2026-02-20 after v2.0 milestone started*
