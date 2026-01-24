# External Integrations

**Analysis Date:** 2026-01-24

## APIs & External Services

**Email Service:**
- SMTP email backend via Gmail or custom SMTP
  - Uses Django's `EmailMultiAlternatives` for HTML + text support
  - Configuration: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
  - Default: Console backend in development (prints to stdout)
  - In production: SMTP (requires `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`)
  - Implementation: `apps/core/email.py` with functions:
    - `send_email()` - Generic template-based email sender
    - `send_weekly_summary_email()` - Weekly dashboard summary
    - `send_late_pledge_alert()` - Overdue pledge notifications
    - `send_at_risk_donor_alert()` - At-risk donor notifications
    - `send_password_reset_email()` - Password reset instructions

## Data Storage

**Databases:**
- PostgreSQL 15
  - Connection: Environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)
  - Default: `postgres://donorcrm:donorcrm@localhost:5432/donorcrm` (dev)
  - Client: psycopg2-binary via Django ORM
  - Production: Connection pooling with 20 base connections, 30 overflow, 5-minute recycle

**File Storage:**
- Local filesystem only
  - Static files: Served via Whitenoise in production (`STATIC_ROOT = BASE_DIR / 'staticfiles'`)
  - Media files: Not detected (no external S3/cloud storage integration)

**Caching:**
- Redis 7 (production only)
  - Connection: `REDIS_URL` environment variable (e.g., `redis://localhost:6379/1`)
  - Purpose: Django cache backend
  - Not used in development (in-memory cache)

## Authentication & Identity

**Auth Provider:**
- Custom via Django's User model
  - Location: `apps/users.User` (custom user model)
  - Implementation: JWT tokens via `djangorestframework-simplejwt`

**JWT Configuration:**
- Access token lifetime: 15 minutes (development: 1 hour)
- Refresh token lifetime: 7 days (development: 30 days)
- Token rotation: Enabled
- Blacklist after rotation: Enabled
- Token storage: Client-side (no server-side session required)
- Implementation: `apps/users/views_auth.py` and DRF JWT auth class

**Password Management:**
- Standard Django password validators (length, similarity, common passwords, numeric)
- Password reset via email with token
- Email function: `send_password_reset_email()` in `apps/core/email.py`

## Monitoring & Observability

**Error Tracking:**
- Sentry (production only)
  - DSN: `SENTRY_DSN` environment variable
  - Integrations: Django, Celery
  - Trace sample rate: 10% (0.1)
  - PII redaction: Enabled (no default PII sent)
  - Implementation: `config/settings/prod.py`

**Logs:**
- Console output via Python logging
- Formatters: Simple (dev), Verbose (prod)
- Levels: DEBUG (dev), INFO (default), WARNING (prod root)
- Handlers:
  - `django` logger: Configured per `DJANGO_LOG_LEVEL` env var
  - `apps` logger: DEBUG level for application code
- All logs stream to stdout (suitable for container/Docker logging)

**Health Checks:**
- Health endpoint: `/api/v1/health/` (referenced in render.yaml)
- Implementation: `apps/core/` (endpoint location TBD - check views)

## CI/CD & Deployment

**Hosting:**
- Render.com (primary deployment target)
  - Frontend: Static site at `donorcrm-frontend.onrender.com`
  - Backend: Web service at `donorcrm-web.onrender.com`
  - Database: Render PostgreSQL (free tier)
  - No Redis/Celery in production (disabled to reduce costs)

**Alternative Deployment:**
- Docker Compose (local development)
- Railway (per railway.toml)
- Docker containers with Gunicorn

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, or other CI config found)

**Build Process (Backend):**
- Requirements: `pip install -r requirements/prod.txt`
- Static files: `python manage.py collectstatic --noinput`
- Server: `gunicorn config.wsgi:application`

**Build Process (Frontend):**
- Node.js 22
- Command: `npm install && npx vite build`
- Output: Static files to `./dist` directory
- Served via Render static site

## Environment Configuration

**Required Environment Variables (Production):**
- `SECRET_KEY` - Django secret (auto-generated via Render)
- `DEBUG` - Must be `False`
- `ALLOWED_HOSTS` - `donorcrm-web.onrender.com`
- `CORS_ALLOWED_ORIGINS` - `https://donorcrm-frontend.onrender.com`
- `DATABASE_URL` - PostgreSQL connection string (from Render database)
- `DJANGO_SETTINGS_MODULE` - `config.settings.prod`
- `EMAIL_BACKEND` - SMTP backend configuration
- `SENTRY_DSN` - (optional, only if error tracking enabled)

**Required Environment Variables (Development):**
- `DEBUG` - `True`
- `SECRET_KEY` - Any value (not sensitive in dev)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` - PostgreSQL connection
- `REDIS_URL` - Redis connection for Celery
- `CORS_ALLOWED_ORIGINS` - `http://localhost:3000,http://127.0.0.1:3000`

**Secrets Location:**
- Render: Environment variables in deployment settings
- Development: `.env` file (git-ignored via `.gitignore`)
- Example template: `.env.example`

## Webhooks & Callbacks

**Incoming:**
- Not detected (no webhook endpoints found)

**Outgoing:**
- Not detected (no external webhook calls found)

## Email Templates

**Templates Location:** `templates/emails/` directory

**Available Templates:**
- `weekly_summary.txt` / `weekly_summary.html` - Weekly dashboard summary
- `late_pledge_alert.txt` / `late_pledge_alert.html` - Overdue pledge notification
- `at_risk_donors_alert.txt` / `at_risk_donors_alert.html` - At-risk donor notifications
- `password_reset.txt` / `password_reset.html` - Password reset instructions

Each template has optional HTML variant (graceful fallback to text-only if HTML not available).

## Async Task System

**Framework:** Celery 5.3 with Redis broker

**Task Locations:**
- `apps/contacts/tasks.py` - At-risk donor detection
- `apps/pledges/tasks.py` - Late pledge checking
- `apps/dashboard/tasks.py` - Weekly summary generation
- `apps/imports/tasks.py` - CSV import/export processing

**Task Execution:**
- Broker: Redis (slot 0)
- Result backend: Redis (same instance)
- JSON serialization for language-agnostic message passing
- Celery Beat scheduler: `celery -A config beat -l info` for periodic task execution

---

*Integration audit: 2026-01-24*
