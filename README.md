# DonorCRM-SPO

A purpose-built CRM for missionaries and nonprofit fundraisers at Saint Paul's Outreach (SPO). Simple, motivating, and actually used.

- **Frontend**: [donorcrm-frontend.onrender.com](https://donorcrm-frontend.onrender.com)
- **Backend API**: [donorcrm-web.onrender.com](https://donorcrm-web.onrender.com)

---

## What is DonorCRM

DonorCRM is a minimalist donor relationship management system for individual fundraisers — specifically missionaries at organizations like Saint Paul's Outreach. It tracks gifts, manages recurring pledges, maintains donor relationships, and provides leadership with cross-missionary analytics.

The problem it solves: missionaries spend too much time maintaining spreadsheets and not enough time building relationships. Most CRMs are built for sales teams or large nonprofits. They're bloated, confusing, and poorly adopted. DonorCRM strips down to what a missionary actually needs day-to-day: who gave, who stopped, who needs a thank-you, and how close am I to my goal.

Built from research into missionary support-raising workflows, DonorCRM delivers essential CRM functionality — dashboard KPIs, contact management, pledge tracking, journal pipelines, goal progress — without the complexity that drives low adoption. It currently serves 100+ fundraising staff at SPO.

---

## Key Features

- **Dashboard** — personalized tile grid with KPIs, charts, alerts, and action items. Drag-and-drop ordering, 12 configurable tiles including giving summary, support progress, thank-you queue, and MPD financial overview
- **Contact & Donor Management** — full CRUD with search, filtering, tagging, giving history, and denormalized stats (total given, gift count, last gift date)
- **Journal Pipeline** — 7-stage fundraising campaign tracker (Contact > Scheduled > Meet > Close > Decision > Thank > Next Steps) with interactive grid UI, event logging, decision tracking, and analytics
- **Goal Tracking** — monthly support goal with progress bars, pacing targets, decisions progress bar, and journal selection for activity metrics
- **MPD Resources** — curated links and pacing calculator for missionary partner development
- **Broadcast Tasks** — leadership can create broadcast tasks distributed to multiple missionaries with individual completion tracking and cascade editing
- **CSV Import Pipeline** — bulk import from Raiser's Edge CSVs (Solicitors, Constituents, Gifts, Recurring Gifts) and Smartsheet MPD reports with validation, dedup, and audit trail
- **View As** — supervisors and admins can view any missionary's dashboard and data in read-only mode (mutations blocked by middleware)
- **Role-Based Access Control** — four active roles: missionary, supervisor, coach, admin. Contact ownership is the primary data isolation boundary
- **Insights & Analytics** — donations by month/year, monthly commitments, late donations, follow-up tracking, transaction history, and admin team performance dashboards
- **Prayer Tracker** — prayer intentions linked to contacts and gifts with focus mode
- **Duplicate Detection & Merge** — identify and merge duplicate contacts with audit trail

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Django | 4.2 | Web framework |
| Django REST Framework | 3.14+ | API layer |
| simplejwt | 5.3+ | JWT authentication (15-min access, 7-day refresh) |
| django-filter | 24.3 (pinned) | API filtering |
| drf-spectacular | 0.27+ | OpenAPI/Swagger docs |
| PostgreSQL | 15 | Database |
| Celery + Redis | 5.3+ / 5.0+ | Async tasks (disabled in production) |
| django-csp | 4.0+ | Content Security Policy |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19.2 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7.2 | Build tool |
| Tailwind CSS | 3.4 | Styling |
| shadcn/ui (Radix) | latest | Component primitives |
| TanStack React Query | 5.90 | Server state management |
| TanStack React Table | 8.21 | Data tables |
| nuqs | 2.8 | URL-based filter state |
| Recharts | 3.6 | Charts and visualizations |
| @dnd-kit | 6.3 | Drag-and-drop (dashboard tiles) |
| Sonner | 2.0 | Toast notifications |
| Axios | 1.13 | HTTP client |
| Playwright | latest | E2E testing |

### Infrastructure

| Component | Platform | Type |
|-----------|----------|------|
| Frontend | Render | Static site (CDN) |
| Backend | Render | Web service (gunicorn) |
| Database | Render | Managed PostgreSQL |
| CI/CD | GitHub → Render | Auto-deploy on push to main |

---

## Architecture Overview

### Data Flow

```
User → React SPA → Axios (JWT + View As header) → Django DRF View
                                                      │
                                                      ├── Permission check (role + get_visible_user_ids)
                                                      ├── ViewAsMiddleware (if X-View-As-User-Id header)
                                                      ├── FilterBackend (django-filter)
                                                      └── Service layer → ORM → PostgreSQL
                                                              │
                                                              └── JSON Response → React Query cache → UI render
```

### Core Concepts

- **Contact ownership** — `Contact.owner` is the primary data isolation boundary. All dashboard calculations, analytics, and permission checks flow from this FK to User
- **Gift credit splitting** — Gift → GiftCredit → Solicitor → User. Recurring gifts follow the same pattern. Contact ownership is assigned based on credited solicitor
- **Permission model** — `get_visible_user_ids(user, request)` is the centralized function determining whose data a user can see. Every list view, analytics query, and export flows through it
- **Service layer** — business logic lives in `services.py` files, not in views or models
- **Money in cents** — all monetary values stored as integer cents (`PositiveBigIntegerField`). Conversion happens at serializer or frontend display level

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 22+
- PostgreSQL 15+ (or Docker)
- Redis 7+ (optional, for Celery)

### Backend Setup

```bash
git clone https://github.com/matkukla/DonorCRM-SPO.git
cd DonorCRM-SPO

python3 -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt

# Start PostgreSQL and Redis via Docker
docker compose up -d db redis

# Run migrations and seed data
python manage.py migrate
python manage.py create_test_accounts

# Start dev server
python manage.py runserver    # http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### Full Stack (Docker)

```bash
docker compose up --build     # Starts: db, redis, web, celery, celery-beat
```

### Running Tests

```bash
# Backend (uses SQLite in-memory, no DB needed)
source venv/bin/activate
pytest
pytest apps/contacts/tests/test_views.py -k "test_list"   # Single test
pytest -m "not slow"                                        # Skip slow tests

# Frontend
cd frontend
npm run build     # TypeScript check + Vite build
npm run lint      # ESLint

# E2E (Playwright)
cd frontend
npx playwright test                         # Run all E2E specs
npx playwright test e2e/dashboard.spec.ts   # Single spec
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (auto-set by Render) |
| `SECRET_KEY` | Django secret key |
| `ALLOWED_HOSTS` | Domain whitelist |
| `CORS_ALLOWED_ORIGINS` | Frontend URL for CORS |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` or `config.settings.prod` |

---

## Deployment

DonorCRM deploys automatically from GitHub to Render on push to `main`.

| Service | Type | Description |
|---------|------|-------------|
| donorcrm-frontend | Static Site | React SPA served via CDN |
| donorcrm-web | Web Service | Django API server (gunicorn) |
| donorcrm-db | PostgreSQL | Managed database |

Build command (web service):
```
pip install -r requirements/prod.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
```

Note: Celery/Redis are disabled in production to reduce hosting costs. All operations are synchronous.

---

## Project Structure

```
DonorCRM/
├── apps/                       # Django backend apps
│   ├── contacts/               # Contact CRUD, ownership, search, denormalized stats
│   ├── gifts/                  # Gift, RecurringGift, Solicitor, credit splitting
│   ├── tasks/                  # Tasks + broadcast task system
│   ├── journals/               # 7-stage pipeline, decisions, next steps
│   ├── groups/                 # Contact tags and segments
│   ├── events/                 # Notification feed (GenericForeignKey)
│   ├── prayers/                # Prayer intentions linked to contacts/gifts
│   ├── dashboard/              # Aggregated views, service functions (12 tiles)
│   ├── insights/               # Analytics endpoints and services
│   ├── imports/                # CSV import (RE, Smartsheet, generic), Fund, MPDSnapshot
│   ├── users/                  # User model, roles, goals, admin management commands
│   └── core/                   # Base model, permissions, middleware, utilities
├── config/                     # Django settings (base/dev/test/prod), URLs, WSGI
├── frontend/src/
│   ├── pages/                  # Route-level components (lazy-loaded)
│   ├── components/             # Shared + feature-specific UI components
│   ├── api/                    # Typed API client functions (one file per resource)
│   ├── hooks/                  # React Query hooks (one file per resource)
│   ├── providers/              # Auth, Query, Theme, ViewAs context providers
│   ├── lib/                    # Utilities (formatLocalDate, cn, toQueryParams)
│   └── types/                  # TypeScript type definitions
├── requirements/               # Python deps (base.txt, dev.txt, prod.txt)
├── render.yaml                 # Render deployment blueprint
└── docker-compose.yml          # Local development
```

---

## Team

Built by **JR** (product strategy, prompt architecture) and **Matthew** (engineering via Claude Code).

Contact: [mkukla1105@gmail.com](mailto:mkukla1105@gmail.com)

---

## Milestones

| Version | Name | Phases | Date |
|---------|------|--------|------|
| v1.0 | Journal Feature | 6 | 2026-01-29 |
| v1.1 | CSV Import | 6 | 2026-02-04 |
| v1.2 | Admin Analytics Dashboard | 7 | 2026-02-16 |
| v1.3 | Smartsheet Import, Filters & Polish | 7 | 2026-02-19 |
| v2.0 | Import Revamp, Prayer Intentions & Dashboard Polish | 10 | 2026-02-25 |
| v2.1 | Security Hardening | 1 | 2026-02-25 |
| v2.2 | UI Polish, Journal Report & Supervisor Role | 10 | 2026-03-11 |
| v2.3 | Goal Tracking & View As | 9 | 2026-03-25 |
| — | Duplicate Contact Checking & Merging | 1 | 2026-03-28 |
| — | Dashboard Performance (Phase 1), Bug Fixes & E2E Infrastructure | — | 2026-04 (current) |

---

## Design Principles

1. **Every feature must justify its existence** — if it doesn't serve a daily workflow, it doesn't ship
2. **Clarity over completeness** — better to do 5 things excellently than 50 things poorly
3. **Feedback loops matter** — users need to see their actions acknowledged
4. **Reduce cognitive load** — present minimum information needed to make decisions
5. **Progressive disclosure** — hide complexity behind clear paths

---

*"A CRM should feel like a helpful assistant who knows exactly what you need to do today, not a database you have to maintain."*
