# Technology Stack

**Analysis Date:** 2026-01-24

## Languages

**Primary:**
- Python 3.11 - Backend API and async task processing via Django and Celery
- TypeScript 5.9 - Frontend application with React
- JavaScript/Node.js 22 - Frontend build tooling and package management

**Secondary:**
- SQL - PostgreSQL database queries and migrations

## Runtime

**Environment:**
- Python 3.11 (slim Docker image from `python:3.11-slim`)
- Node.js 22 (via render.yaml)

**Package Manager:**
- pip (Python) - with requirements split into `base.txt`, `dev.txt`, `prod.txt`
- npm - JavaScript/Node.js dependencies

## Frameworks

**Backend:**
- Django 4.2 - Web framework and ORM
- Django REST Framework (DRF) 3.14 - REST API development
- djangorestframework-simplejwt 5.3 - JWT authentication and token management
- Celery 5.3 - Distributed task queue for async jobs
- drf-spectacular 0.27 - OpenAPI schema generation and API documentation

**Frontend:**
- React 19 - UI framework
- Vite 7 - Build tool and dev server
- React Router 6.30 - Client-side routing
- TanStack React Query 5.90 - Data fetching and caching
- TanStack React Table 8.21 - Advanced table component

**UI Components:**
- Radix UI (dialog, dropdown-menu, separator, slot, tabs) - Unstyled, accessible component library
- Tailwind CSS 3.4 - Utility-first CSS framework
- Lucide React 0.562 - Icon library

**Testing (Backend):**
- pytest 7.4 - Test runner
- pytest-django 4.5 - Django plugin for pytest
- pytest-cov 4.1 - Coverage reporting
- factory-boy 3.3 - Test data factories
- faker 19 - Fake data generation

**Testing (Frontend):**
- Not detected

**Code Quality:**
- Black 23 - Python code formatting
- isort 5.12 - Python import sorting
- flake8 6 - Python linting
- ESLint 9.39 - JavaScript linting
- TypeScript 5.9 - Type checking

**Development Tools:**
- django-debug-toolbar 4.2 - Django development debugging
- django-extensions 3.2 - Django management commands
- IPython 8 - Enhanced Python REPL

## Key Dependencies

**Critical (Backend):**
- djangorestframework-simplejwt 5.3 - JWT token management for API authentication
- celery 5.3 - Async task execution (email sending, scheduled reports, at-risk detection)
- redis 5 - In-memory broker/cache for Celery
- psycopg2-binary 2.9 - PostgreSQL database driver
- django-db-connection-pool 1.2.0 - Connection pooling for PostgreSQL

**Infrastructure:**
- gunicorn 21 - Production WSGI server
- whitenoise 6.6 - Static file serving in production
- sentry-sdk 1.30 - Error tracking and monitoring (production only)
- django-cors-headers 4 - CORS middleware

**Utilities:**
- python-dateutil 2.8 - Date/time utilities
- python-decouple 3.8 - Environment variable management
- django-filter 23 - Queryset filtering for APIs
- axios 1.13 - HTTP client for frontend API calls
- recharts 3.6 - Charting library for React dashboards

## Configuration

**Environment:**
- Environment variables via `python-decouple` (reads `.env` file)
- Configuration splits: `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`, `config/settings/test.py`
- Active settings via `DJANGO_SETTINGS_MODULE` environment variable (defaults to `config.settings.dev`)

**Key Environment Variables:**
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode toggle
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL connection
- `REDIS_URL` - Redis connection for Celery (e.g., `redis://localhost:6379/0`)
- `CORS_ALLOWED_ORIGINS` - Comma-separated CORS origins
- `EMAIL_BACKEND` - Email backend (console for dev, SMTP for prod)
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` - SMTP configuration
- `SENTRY_DSN` - Sentry error tracking (production)
- `ENVIRONMENT` - Environment name for Sentry
- `DJANGO_LOG_LEVEL` - Django logging level

**Frontend Environment:**
- `VITE_API_BASE_URL` - API base URL for frontend (e.g., `https://donorcrm-web.onrender.com/api/v1`)

**Build Configuration:**
- `vite.config.ts` - Vite build configuration with React plugin and `@` path alias
- `tsconfig.json` - TypeScript configuration (references `tsconfig.app.json` and `tsconfig.node.json`)
- `tailwind.config.js` - Tailwind CSS configuration
- `postcss.config.js` - PostCSS configuration
- `eslint.config.js` - ESLint configuration
- `pyproject.toml` - Black, isort, pytest, coverage configuration

## Platform Requirements

**Development:**
- Python 3.11
- Node.js 22
- PostgreSQL 15 (via Docker)
- Redis 7 (via Docker)
- Docker and docker-compose for local infrastructure

**Production:**
- Render.com hosting (or any platform supporting Docker and buildpacks)
- PostgreSQL database (Render managed or external)
- Node.js 22 for frontend builds
- Python 3.11 for backend
- Gunicorn WSGI server
- No Redis required unless Celery is enabled (currently commented out in render.yaml)

## Database

**Engine:**
- PostgreSQL 15 (via `django.db.backends.postgresql`)

**Connectivity:**
- Production: Connection pooling via `django-db-connection-pool` with 20 base connections and 30 overflow
- Pool settings: 5-minute recycle interval, pre-ping enabled

**Features:**
- Custom User model at `apps.users.User`
- All migrations stored in `*/migrations/` directories per app
- Large auto fields (`BigAutoField`) for primary keys

## Caching

**Development:**
- In-memory cache (default Django behavior)

**Production:**
- Redis (via `django.core.cache.backends.redis.RedisCache`)
- Location: `REDIS_URL` environment variable (e.g., `redis://localhost:6379/1`)

## Task Queue

**System:**
- Celery 5.3 with Redis broker
- Broker URL: `REDIS_URL` (typically slot 0)
- Result backend: `REDIS_URL`
- Task serialization: JSON
- Time limits: 5-minute soft limit, 10-minute hard limit per task
- Prefetch multiplier: 1 (prevent task hoarding)
- Acknowledgment: Late (after task completes for reliability)

**Periodic Tasks (via Celery Beat):**
- `check-late-pledges-daily`: Daily at 6 AM UTC (detects overdue pledge payments)
- `detect-at-risk-donors-daily`: Daily at 7 AM UTC (flags donors inactive 60+ days)
- `generate-weekly-summary`: Mondays at 8 AM UTC (generates summary reports)

---

*Stack analysis: 2026-01-24*
