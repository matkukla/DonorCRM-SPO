# DonorCRM

## What This Is

A donor relationship management system for missionaries. Includes contact management, donation tracking, pledge management, task system, Journal feature for fundraising campaign pipelines, and SPO-compatible CSV import. Now adding an Admin Analytics Dashboard for coaches and leadership to monitor missionary performance across the organization.

## Core Value

Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems.

## Current Milestone: v1.2 Admin Analytics Dashboard

**Goal:** Give coaches and leadership cross-missionary visibility into fundraising activity, pipeline health, and stalled contacts — so they can proactively support their teams.

**Target features:**
- Dashboard Overview page with summary cards, team activity table, conversion funnel (journal pipeline), trend chart, and alerts panel
- Stalled Contacts page with 14+ day inactivity detection, pagination, and sorting
- User Detail page with per-missionary performance trends and journal listings
- User Drilldown panel (slide-in sidebar for quick inspection)
- 5 API endpoints with ADMIN/FINANCE role-based visibility
- Drill-down charts (click funnel segments to see underlying contacts)
- Comparison mode (time periods or users side-by-side)
- Activity heatmap calendar view

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

### Active

- [ ] Dashboard Overview page with summary cards and alerts
- [ ] Team activity table showing all missionaries' recent actions
- [ ] Conversion funnel visualizing journal pipeline stages across org
- [ ] Trend chart for donations/pledges over time
- [ ] Stalled Contacts page (14+ days no activity) with pagination/sorting
- [ ] User Detail page with per-missionary performance and journal listings
- [ ] User Drilldown panel (slide-in sidebar)
- [ ] Drill-down charts (click funnel/chart to see underlying contacts)
- [ ] Comparison mode (time periods or users side-by-side)
- [ ] Activity heatmap calendar view
- [ ] 5 API endpoints with ADMIN/FINANCE role-based visibility
- [ ] Pace calculation and stalled detection business logic

### Out of Scope

- Real-time updates via WebSocket/SSE — polling sufficient for dashboard
- Email digest reports — no email infrastructure yet
- Performance scoring/gamification — could demotivate missionaries
- Projected outcomes with confidence intervals — over-engineering for v1.2
- Saved filter views — defer to future
- Mobile-optimized activity logging — web responsive sufficient
- Import progress tracking — already adequate in Import Center
- Audit log for compliance — defer to future
- Custom stage definitions — fixed 6-stage pipeline
- AI-generated suggestions — manual workflow only

## Context

### Existing Codebase
- Django 4.2 + DRF backend, React 19 + TypeScript + Vite frontend
- PostgreSQL with Django ORM, UUID primary keys via TimeStampedModel base
- Tailwind CSS + Radix UI components, Recharts for charts
- Owner-scoped data model (Contact.owner, Task.owner pattern)
- Permission classes: IsContactOwnerOrReadAccess, IsStaffOrAbove, IsAdmin
- Celery for async tasks (currently disabled in production)
- Existing apps: users, contacts, donations, pledges, tasks, groups, events, dashboard, imports

### Domain Context
- Primary user: individual missionary fundraiser
- Workflow: identify prospects → contact → meet → ask → track decision → thank → plan next
- A "journal" represents a fundraising campaign/push (e.g., "Spring 2026 Support Raising")
- Missionaries track multiple donors through the pipeline simultaneously
- Decision tracking is critical: amount pledged, cadence, and status changes over time
- Organization leadership and coaches (10-20 people) need cross-missionary visibility
- Coaches oversee multiple missionaries and need to identify who is stalled or struggling

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
- **Charts**: Recharts (already a dependency)
- **Performance**: Report queries must avoid N+1; use select_related/prefetch_related and aggregation
- **Compatibility**: New models must work with existing Contact, Task, User models

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django/DRF over Node/Prisma | Follow existing codebase patterns | — Pending |
| Link journal tasks to existing Task model | Avoid duplicate task systems, reuse existing UI | — Pending |
| Owner + admin visibility for journals | Supports future cross-missionary analytics without full admin UI | — Pending |
| Contact "Journals" as new tab | Keep contact detail focused, journals is substantial enough for own tab | — Pending |
| Fixed 6-stage pipeline | Matches missionary fundraising workflow, avoid over-engineering | — Pending |
| Cents for money storage | Precision, no floating point issues, matches pledge patterns | — Pending |

---
*Last updated: 2026-02-12 after v1.2 milestone start*
