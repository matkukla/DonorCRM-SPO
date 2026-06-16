# DonorCRM-SPO

A purpose-built CRM for missionaries and nonprofit fundraisers at Saint Paul's Outreach (SPO). It strips donor relationship management down to what a fundraiser actually needs day-to-day — who gave, who stopped, who needs a thank-you, and how close they are to goal — without the bloat that drives low adoption. Currently serves 100+ fundraising staff at SPO.

- **Frontend**: [donorcrm-frontend.onrender.com](https://donorcrm-frontend.onrender.com)
- **Backend API**: [donorcrm-web.onrender.com](https://donorcrm-web.onrender.com)

## Features

- **Dashboard** — drag-and-drop tile grid with KPIs, charts, alerts, and action items (giving summary, support progress, thank-you queue, MPD financial overview)
- **Contact & donor management** — full CRUD with search, filtering, tagging, giving history, and denormalized stats
- **Journal pipeline** — 7-stage fundraising tracker (Contact → Scheduled → Meet → Close → Decision → Thank → Next Steps) with event logging and analytics
- **Goal tracking** — monthly support goal with progress bars and pacing targets
- **CSV import** — bulk import from Raiser's Edge and Smartsheet MPD reports with validation, dedup, and audit trail
- **View As** — supervisors/admins view any missionary's data read-only (mutations blocked by middleware)
- **Role-based access** — missionary, supervisor, coach, admin; contact ownership is the data isolation boundary
- **Insights** — donations by period, late donations, follow-ups, and team performance dashboards
- **Prayer tracker** and **duplicate detection/merge**

## Tech Stack

**Backend** — Django 4.2 + DRF, JWT auth (simplejwt), django-filter (pinned 24.3), drf-spectacular, PostgreSQL 15, Celery + Redis (disabled in prod), django-csp.

**Frontend** — React 19 + TypeScript + Vite, Tailwind CSS, shadcn/ui (Radix), TanStack Query & Table, nuqs (URL filter state), Recharts, @dnd-kit, Axios, Playwright (E2E).

**Infrastructure** — Render: static site (frontend), gunicorn web service (backend), managed PostgreSQL. Auto-deploys on push to `main`.

## Architecture

- **Contact ownership** (`Contact.owner`) is the primary data isolation boundary — all dashboard calculations, analytics, and permission checks flow from it.
- **`get_visible_user_ids(user, request)`** is the centralized choke point for whose data a user can see; every list view, analytics query, and export goes through it.
- **Gift credit splitting** — Gift → GiftCredit → Solicitor → User. Contact ownership is assigned from the credited solicitor.
- **Money in cents** — all monetary values stored as integer `*_cents` fields; conversion happens at the serializer or display layer.
- **Service layer** — business logic lives in `services.py`, not in views or models.

## Getting Started

**Prerequisites:** Python 3.11+, Node.js 22+, PostgreSQL 15+ (or Docker), Redis 7+ (optional).

```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements/dev.txt
docker compose up -d db redis          # start PostgreSQL + Redis
python manage.py migrate
python manage.py create_test_accounts
python manage.py runserver             # http://localhost:8000

# Frontend
cd frontend && npm install
npm run dev                            # http://localhost:5173

# Full stack (db, redis, web, celery, celery-beat)
docker compose up --build
```

### Tests

```bash
pytest                                 # backend (SQLite in-memory, no DB needed)
pytest -m "not slow"                   # skip slow tests
cd frontend && npm run build           # TypeScript check + Vite build
cd frontend && npm run lint            # ESLint
cd frontend && npx playwright test     # E2E
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (auto-set by Render) |
| `SECRET_KEY` | Django secret key |
| `ALLOWED_HOSTS` | Domain whitelist |
| `CORS_ALLOWED_ORIGINS` | Frontend URL for CORS |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` or `config.settings.prod` |

## Project Structure

```
apps/         # Django apps: contacts, gifts, tasks, journals, groups, events,
              #   prayers, dashboard, insights, imports, users, core
config/       # Settings (base/dev/test/prod), URLs, WSGI
frontend/src/ # pages, components, api (typed clients), hooks (React Query),
              #   providers, lib, types
requirements/ # Python deps (base.txt, dev.txt, prod.txt)
render.yaml   # Render deployment blueprint
docker-compose.yml
```

## Team

Built by **JR** (product strategy) and **Matthew** (engineering). Contact: [mkukla1105@gmail.com](mailto:mkukla1105@gmail.com)
