# DonorCRM — Journal Feature

## What This Is

A fundraising campaign pipeline tool ("Journal") for individual missionaries using DonorCRM. Each journal tracks a set of contacts through sequential fundraising stages (Contact → Meet → Close → Decision → Thank → Next Steps) with per-contact event logging, decision tracking with history, and generated reports. The UI is a clean grid with contacts as rows and stages as columns, inspired by DonorElf's layout.

## Core Value

A missionary can look at their journal and instantly know what's next for each donor and what they've completed so far.

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

### Active

- [ ] Journal CRUD (create, edit, archive) with goal amount + optional deadline
- [ ] Add/remove contacts to journals (many-to-many, concurrent membership)
- [ ] Stage event logging across 6 stages with typed events per stage
- [ ] Sequential-but-flexible pipeline (skip/revisit stages, subtle warnings)
- [ ] Decision tracking with current state + full history
- [ ] Decision cadence support (one-time, monthly, quarterly, annual)
- [ ] Next Steps as a checklist per contact per journal
- [ ] Journal detail page with grid view (contacts × stages)
- [ ] Stage cells with checkmarks, hover tooltips, and event timeline drawers
- [ ] Decision column with amount/cadence/status cards
- [ ] Journal header with goal, progress, decisions made
- [ ] Report tab with decision trends, stage activity, pipeline breakdown, next steps queue
- [ ] Contact detail "Journals" tab showing associated journals
- [ ] Link journal tasks to existing Task system (add journal_id to Task)
- [ ] Owner + admin visibility (owner sees theirs, admins see all)
- [ ] Admin analytics foundation (endpoints for cross-missionary aggregation)
- [ ] Search/filter contacts within journal grid
- [ ] Add Contacts picker for journal membership

### Out of Scope

- Admin UI for cross-missionary analytics — data model supports it, UI deferred
- Real-time collaboration/multi-user editing — single-user focused
- Email/SMS integration for stage actions — log events only, no sending
- Mobile-native app — web responsive is sufficient
- Bulk journal operations — one journal at a time
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
- Organization leadership needs cross-missionary visibility (future admin analytics)

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
*Last updated: 2026-01-24 after initialization*
