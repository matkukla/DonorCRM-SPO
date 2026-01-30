# DonorCRM

## What This Is

A donor relationship management system for missionaries. Includes contact management, donation tracking, pledge management, task system, and a Journal feature for fundraising campaign pipelines. Now adding SPO-compatible CSV import for bulk data ingestion from DonorElf exports.

## Core Value

Missionaries can manage donor relationships efficiently, with accurate data imported from their organization's systems.

## Current Milestone: v1.1 CSV Import

**Goal:** Enable admins to import SPO-exported CSV files (Funds, Entities, Transactions, Pledges) into DonorCRM with validation, preview, and idempotent upserts.

**Target features:**
- Import Center UI for 4 CSV types
- Fund model for account/campaign tracking
- External ID support for idempotent imports
- Row-level validation and error reporting
- Import audit trail (ImportRun, ImportRowError)

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

### Active

- [ ] Fund model for account/campaign tracking (external_id for upsert)
- [ ] External ID fields on Contact, Donation, Pledge for idempotent imports
- [ ] ImportRun model for audit trail (type, status, counts, uploaded_by)
- [ ] ImportRowError model for row-level error tracking
- [ ] CSV parser with mapping specs per file type
- [ ] Funds CSV import (fund_id, name, status)
- [ ] Entities CSV import → Contact (entity_id, name, email, phone, address)
- [ ] Transactions CSV import → Donation (transaction_id, entity_id, fund_id, amount, date)
- [ ] Pledges CSV import → Commitment (pledge_id, entity_id, fund_id, amount, cadence, status)
- [ ] Import Center UI with 4 tiles (Funds, Entities, Transactions, Pledges)
- [ ] Upload → Preview → Validate → Import workflow
- [ ] Validation report (missing columns, parse errors, orphan references)
- [ ] Import results summary (created/updated/skipped/errors)
- [ ] Download errors CSV functionality
- [ ] Admin-only access to Import Center

### Out of Scope

- Admin UI for cross-missionary analytics — data model supports it, UI deferred
- Real-time collaboration/multi-user editing — single-user focused
- Email/SMS integration for stage actions — log events only, no sending
- Mobile-native app — web responsive is sufficient
- Bulk journal operations — one journal at a time
- Custom stage definitions — fixed 6-stage pipeline
- AI-generated suggestions — manual workflow only
- Complex ETL tooling or Celery queues — synchronous import for MVP
- Manual Excel editing as part of normal flow — fix via mapping rules + validation
- Non-strict mode (allowing unmatched references) — strict mode only for v1.1

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
*Last updated: 2026-01-30 after v1.1 milestone start*
