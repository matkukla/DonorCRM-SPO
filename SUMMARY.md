# DonorCRM — Summary

A purpose-built CRM for missionaries and nonprofit fundraisers at Saint Paul's Outreach (SPO). Minimalist, workflow-focused, and actually used — currently serving 100+ fundraising staff.

## What It Does

Tracks gifts, manages recurring pledges, maintains donor relationships, and provides leadership with cross-missionary analytics. Strips down to what a missionary actually needs: who gave, who stopped, who needs a thank-you, and how close am I to my goal.

## Key Features

- **Dashboard** — 12 configurable tiles (KPIs, charts, alerts, thank-you queue, MPD overview) with drag-and-drop ordering
- **Contact & Donor Management** — full CRUD with search, filtering, tagging, giving history, denormalized stats
- **Journal Pipeline** — 7-stage fundraising tracker (Contact → Scheduled → Meet → Close → Decision → Thank → Next Steps)
- **Goal Tracking** — monthly support goal with pacing targets and progress bars
- **Broadcast Tasks** — leadership distributes tasks to multiple missionaries with per-user tracking
- **CSV Imports** — Raiser's Edge and Smartsheet pipelines with validation, dedup, audit trail
- **View As** — supervisors/admins view any missionary's data in read-only mode
- **Insights & Analytics** — donation trends, late donations, admin team performance dashboards
- **Prayer Tracker** — prayer intentions linked to contacts and gifts
- **Duplicate Detection & Merge** — identify and merge duplicates with audit trail

## Tech Stack

**Backend:** Django 4.2, DRF, JWT auth (simplejwt), PostgreSQL 15, Celery + Redis (disabled in prod), drf-spectacular
**Frontend:** React 19, TypeScript 5.9, Vite 7, Tailwind, shadcn/ui, TanStack React Query + Table, nuqs, Recharts, Playwright
**Infrastructure:** Render (static site + web service + managed Postgres), auto-deploy from GitHub on push to `main`

## Architecture Essentials

- **Contact ownership** is the primary data isolation boundary — `Contact.owner` FK to User
- **Permission model** centralized in `get_visible_user_ids(user, request)` — every list view, query, and export flows through it
- **Money in cents** — stored as integer `PositiveBigIntegerField`, converted at serializer/display level
- **Gift credit splitting** — Gift → GiftCredit → Solicitor → User
- **Service layer** — business logic in `services.py`, not views or models
- **Base model** — `TimeStampedModel` (UUID PK, `created_at`, `updated_at`) inherited by all models

## Roles

Four active roles: `admin`, `missionary`, `supervisor`, `coach`. Role determines data scope via `get_visible_user_ids()`.

## Project Layout

```
apps/           Django backend (contacts, gifts, tasks, journals, dashboard, insights, imports, users, core, ...)
config/         Django settings split (base/dev/test/prod)
frontend/src/   React SPA (pages, components, api/, hooks/, providers/, lib/, types/)
requirements/   Python deps (base, dev, prod)
render.yaml     Deployment blueprint
```

## Current State

v2.3 shipped (2026-03-25): Goal Tracking & View As. In progress (2026-04): Dashboard Performance (Phase 1), bug fixes, and E2E infrastructure.

## Design Principles

1. Every feature must justify its existence
2. Clarity over completeness
3. Feedback loops matter
4. Reduce cognitive load
5. Progressive disclosure

## Team

Built by **JR** (product strategy, prompt architecture) and **Matthew** (engineering via Claude Code).
