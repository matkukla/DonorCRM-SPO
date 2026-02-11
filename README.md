# DonorCRM

A purpose-built CRM for missionaries and nonprofit staff who raise personal support. Simple, motivating, and actually used.

## Overview

DonorCRM is a minimalist donor relationship management system for individual fundraisers. It tracks gifts, manages pledges, and maintains donor relationships with minimal friction. Built from research into missionary support-raising workflows, it delivers essential CRM functionality without the complexity that drives low adoption.

### Live Demo

- **Frontend**: [donorcrm-frontend.onrender.com](https://donorcrm-frontend.onrender.com)
- **Backend API**: [donorcrm-web.onrender.com](https://donorcrm-web.onrender.com)

## Features

### Dashboard
- Summary of new gifts, donors, and updates since last login
- Prioritized follow-up actions (late donors, pledge expirations)
- Visual progress toward support goals
- At-risk donor early warnings
- Thank-you queue tracking

### Contact Management
- Contact database with search, filtering, and tagging
- Giving history and trends per donor
- Group/segment system for organization

### Donation Tracking
- Individual gift records with automatic contact stat updates
- Denormalized stats (total given, gift count, last gift date) for fast queries

### Pledge Management
- Recurring commitment tracking with status transitions
- Pledge fulfillment monitoring
- Automated alerts for pledge changes

### Journal (Fundraising Campaigns)
- 6-stage pipeline: Contact > Meet > Close > Decision > Thank > Next Steps
- Interactive grid UI with stage cell indicators
- Decision tracking with full history (dual-table pattern)
- Analytics charts (decision trends, stage activity, pipeline breakdown)
- Contact detail integration (Journals tab)
- Task system integration (journal-linked tasks)

### SPO CSV Import (Admin)
- Import Center UI with 4 import types: Funds, Entities, Transactions, Pledges
- Upload > Preview > Validate > Import workflow
- Client-side CSV preview (first 25 rows)
- Row-level validation with error reporting
- Downloadable error CSV for failed rows
- Idempotent upserts via external IDs
- Import audit trail (ImportRun, ImportRowError models)
- Dependency guidance and recommended import order

### Task System
- Reminders with due dates and status tracking
- Link tasks to specific contacts or journals
- Dashboard integration for upcoming/overdue items

### Reporting
- Monthly donation summaries
- Support level vs. goal tracking
- Basic exports for external use (mailings, backups)

### Data Import/Export
- CSV import for donations and contacts
- Export donor lists and giving records
- Built-in duplicate prevention

## Key Workflows

1. **Monitoring Updates**: Log in → See dashboard summary → Identify what needs attention
2. **Following Up**: Review alert → Click donor → Take action (call/email) → Mark complete
3. **Managing Pledges**: Add/update recurring commitments → System tracks fulfillment → Alerts on issues
4. **Thanking Donors**: New gift arrives → Notification appears → Send thank-you → Track completion
5. **Reviewing Status**: Check dashboard trends → Identify lapsed donors → Reach out proactively

## Technology Stack

- **Backend**: Django (Python)
- **Database**: PostgreSQL 
- **Frontend**: React
- **Authentication**: Role-based access control

## Data Model

### Core Entities
- **Users**: Fundraisers, admins, finance staff, read-only viewers
- **Contacts**: Donor and prospect information with ownership
- **Donations**: Individual gift records
- **Pledges**: Recurring giving commitments
- **Tasks**: Reminders and action items
- **Events**: Change log and notification feed
- **Groups**: Contact tags/segments

See full schema documentation in `/docs/data-model.md`

## User Roles

=======
### User Roles
- **Fundraiser**: Manages their own donors, pledges, and tasks
- **Admin**: Full system access, user management, data imports
- **Finance**: Import donations, view giving across organization
- **Read-Only**: View-only access for coaches/supervisors

## Tech Stack

### Backend
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL (UUID primary keys, TimeStampedModel base)
- **Auth**: JWT via djangorestframework-simplejwt
- **Async**: Celery + Redis (disabled in production, synchronous for MVP)
- **API Docs**: drf-spectacular (OpenAPI/Swagger)

### Frontend
- **Framework**: React 19 + TypeScript
- **Build**: Vite
- **Styling**: Tailwind CSS
- **Components**: Radix UI primitives
- **State**: TanStack React Query + React Table
- **Charts**: Recharts
- **CSV**: react-papaparse

### Infrastructure
- **Hosting**: Render (web service + static site + PostgreSQL)
- **CI/CD**: Auto-deploy on push to main

## Project Structure

```
DonorCRM/
├── apps/                   # Django backend apps
│   ├── contacts/           # Contact CRUD, ownership, search
│   ├── donations/          # Gift records, stat updates
│   ├── pledges/            # Recurring commitments
│   ├── tasks/              # Reminders and action items
│   ├── groups/             # Contact tags/segments
│   ├── events/             # Change log and notifications
│   ├── journals/           # Fundraising campaign pipelines
│   ├── imports/            # CSV import (Funds, Entities, Transactions, Pledges)
│   ├── dashboard/          # Aggregated views and reporting
│   ├── insights/           # Analytics endpoints
│   ├── users/              # Auth, roles, JWT
│   └── core/               # Shared models, utilities
├── config/                 # Django settings (dev/prod/test)
├── frontend/               # React/TypeScript SPA
│   └── src/
│       ├── pages/          # Route-level components
│       ├── components/     # Shared UI components
│       └── api/            # API client functions
├── requirements/           # Python dependencies (base/dev/prod)
├── render.yaml             # Render blueprint
└── docker-compose.yml      # Local development
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 22+
- PostgreSQL 15+
- Redis 7+ (optional, for Celery)

### Local Development

```bash
# Clone repository
git clone https://github.com/matkukla/DonorCRM.git
<<<<<<< HEAD
cd donorcrm
=======
cd DonorCRM
>>>>>>> ab18891 (updated documentation)

# Backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/dev.txt

# Start PostgreSQL and Redis (via Docker)
docker compose up -d db redis

# Run migrations and create admin
python manage.py migrate
python manage.py createsuperuser

# Start backend
python manage.py runserver

# Frontend setup (in a new terminal)
cd frontend
npm install
npm run dev
```

The backend runs at `http://localhost:8000` and the frontend at `http://localhost:5173`.

### Docker (Full Stack)

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, Django, Celery worker, and Celery beat.

### Running Tests

```bash
# Backend (411 tests)
source venv/bin/activate
pytest

# With coverage
pytest --cov=apps
```

## Deployment (Render)

DonorCRM is deployed on Render using the [render.yaml](render.yaml) blueprint:

| Service | Type | Description |
|---------|------|-------------|
| donorcrm-frontend | Static Site | React SPA served via CDN |
| donorcrm-web | Web Service | Django API server (gunicorn) |
| donorcrm-db | PostgreSQL | Free-tier database |

**Build command** (web service):
```
pip install -r requirements/prod.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
```

**Environment variables** required:
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Render)
- `SECRET_KEY` - Django secret key
- `ALLOWED_HOSTS` - Domain whitelist
- `CORS_ALLOWED_ORIGINS` - Frontend URL
- `DJANGO_SETTINGS_MODULE` - `config.settings.prod`

## Data Model

### Core Entities
- **Users** - Fundraisers, admins, finance staff, read-only viewers
- **Contacts** - Donor and prospect information with ownership
- **Donations** - Individual gift records (money in cents)
- **Pledges** - Recurring giving commitments with cadence/status
- **Funds** - Account/campaign tracking (SPO import support)
- **Tasks** - Reminders and action items
- **Events** - Change log and notification feed
- **Groups** - Contact tags/segments
- **Journals** - Fundraising campaign pipelines
- **ImportRun / ImportRowError** - Import audit trail

### Key Patterns
- Money stored in cents (integer) for precision
- Owner-scoped data model (`Contact.owner`, `Task.owner`)
- External IDs for idempotent CSV imports
- Denormalized contact stats updated on donation changes
- Decision history via dual-table pattern (current + history)

## Milestones

### v1.0 - Journal Feature (Shipped 2026-01-29)
Journal CRUD, 6-stage pipeline, decision tracking, interactive grid UI, analytics charts, contact/task integration. 6 phases, 24 plans, 35 UAT tests passed.

### v1.1 - CSV Import (Shipped 2026-02-10)
Fund model, external ID fields, 4 CSV import types (Funds, Entities, Transactions, Pledges), Import Center UI, validation/preview workflow, error CSV download. 6 phases, 15 plans, 16 UAT tests passed.

## Design Principles

1. **Every feature must justify its existence** - If it doesn't serve a daily workflow, it doesn't ship
2. **Clarity over completeness** - Better to do 5 things excellently than 50 things poorly
3. **Feedback loops matter** - Users need to see their actions acknowledged
4. **Reduce cognitive load** - Present minimum information needed to make decisions
5. **Progressive disclosure** - Hide complexity behind clear paths

## What We Explicitly Don't Do

To maintain focus and simplicity:
- ❌ Process online donations (integrate with existing platforms)
- ❌ Manage fundraising events or campaigns
- ❌ Track grants or institutional giving
- ❌ Handle volunteer or membership management
- ❌ Replicate accounting functions
- ❌ Send bulk emails

## Roadmap

### MVP (Phase 1)
- [x] Contact management
- [x] Donation tracking
- [x] Pledge management
- [x] Automated alerts
- [x] Task system
- [x] Dashboard
- [x] CSV import/export
- [x] User roles

## Contributing

We welcome contributions that align with our lean, user-focused philosophy. Before adding features:

1. Validate the need with actual users
2. Ensure it serves a daily workflow
3. Keep the UI simple and clear
4. Include tests for reliability

See `CONTRIBUTING.md` for detailed guidelines.

## Support

- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues]
- **Email**: support@yourorg.org

## Research & Background

This project is based on extensive research into missionary fundraising workflows, particularly studying the DonorElf platform and identifying what drives (or prevents) CRM adoption. Key insights:

- Users need actionable prompts, not just data dumps
- Pledge tracking is critical for proactive donor care
- Weekly email summaries drive consistent engagement
- Simple beats comprehensive for adoption rates
- Trust depends on data accuracy and simplicity

Full research document available in `/docs/research.md`

## Acknowledgments

- Research informed by DonorElf usage patterns and missionary support-raising best practices
- Built to serve 100+ fundraising staff at Saint Paul's Outreach
- Designed with feedback from frontline missionaries
=======
- Process online donations (integrate with existing platforms)
- Manage fundraising events or campaigns
- Track grants or institutional giving
- Handle volunteer or membership management
- Replicate accounting functions
- Send bulk emails (export for MailChimp instead)


## License

MIT

*"A CRM should feel like a helpful assistant who knows exactly what you need to do today, not a database you have to maintain."*
