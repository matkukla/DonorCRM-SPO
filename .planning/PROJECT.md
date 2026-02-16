# DonorCRM

## What This Is

A donor relationship management system for missionaries. Includes contact management, donation tracking, pledge management, task system, Journal feature for fundraising campaign pipelines, SPO-compatible CSV import, and an Admin Analytics Dashboard for coaches and leadership to monitor missionary performance across the organization.

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

### Active

*None — ready for next milestone planning*

### Out of Scope

- Real-time updates via WebSocket/SSE — polling sufficient for dashboard
- Email digest reports — no email infrastructure yet
- Performance scoring/gamification — could demotivate missionaries
- Configurable alert thresholds (per coach) — requires user preferences model
- Goal setting & tracking UI — requires new Goal model
- Saved filter views — defer to future
- Mobile-optimized activity logging — web responsive sufficient
- Audit log for compliance — defer to future
- Custom stage definitions — fixed 6-stage pipeline
- AI-generated suggestions — manual workflow only

## Context

### Current State (after v1.2)
- **Backend:** Django 4.2 + DRF, ~21,900 LOC Python (excluding migrations)
- **Frontend:** React 19 + TypeScript + Vite, ~20,900 LOC TypeScript, 127 files
- **Database:** PostgreSQL with Django ORM, UUID primary keys
- **UI:** Tailwind CSS + Radix UI components, Recharts for charts, @uiw/react-heat-map for heatmap
- **Total milestones shipped:** 3 (v1.0, v1.1, v1.2)
- **Total plans executed:** 57 across 19 phases

### Domain Context
- Primary user: individual missionary fundraiser
- Secondary user: coach/supervisor monitoring 5-15 missionaries
- Workflow: identify prospects → contact → meet → ask → track decision → thank → plan next
- A "journal" represents a fundraising campaign/push (e.g., "Spring 2026 Support Raising")
- Missionaries track multiple donors through the pipeline simultaneously
- Decision tracking is critical: amount pledged, cadence, and status changes over time
- Organization leadership and coaches (10-20 people) use analytics dashboard for cross-missionary visibility

### Data Model Decisions
- Money stored in cents (integer) for precision
- Decision has "current" table (unique per journal+contact) and "history" table
- Stage events are append-only log entries, not state transitions
- Next Steps are independent checklist items, not single boolean
- Journal tasks link to existing Task model via journal_id foreign key

## Constraints

- **Tech stack**: Django/DRF backend, React/TypeScript frontend — follow existing patterns
- **Data model**: Use cents for money, UUID PKs, TimeStampedModel base class
- **Access control**: Owner-scoped with admin visibility — follow existing permission patterns
- **UI framework**: Tailwind CSS + Radix UI primitives — match existing component library
- **Charts**: Recharts for standard charts, @uiw/react-heat-map for heatmap
- **Performance**: Report queries must avoid N+1; use select_related/prefetch_related and aggregation
- **Compatibility**: New models must work with existing Contact, Task, User models

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

---
*Last updated: 2026-02-16 after v1.2 milestone*
