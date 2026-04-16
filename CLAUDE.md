# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Django)
```bash
# Start services (PostgreSQL + Redis)
docker compose up -d db redis

# Run backend dev server
source venv/bin/activate
python manage.py runserver

# Run all tests (uses SQLite in-memory, no DB needed)
pytest

# Run single test file or test
pytest apps/contacts/tests/test_views.py
pytest apps/contacts/tests/test_views.py::TestContactList::test_list_own_contacts -k "test_list_own"

# Skip slow/integration tests
pytest -m "not slow"

# Lint
black --check apps/ config/
isort --check-only apps/ config/
flake8 apps/ config/

# Format
black apps/ config/
isort apps/ config/

# Migrations
python manage.py makemigrations
python manage.py migrate
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173
npm run build      # TypeScript check + Vite build
npm run lint       # ESLint
```

### Full Stack (Docker)
```bash
docker compose up --build  # Starts: db, redis, web (:8000), celery, celery-beat
```

## Architecture

### Backend
- **Django 4.2 + DRF** with JWT auth (simplejwt). Settings split: `config/settings/{base,dev,test,prod}.py`
- **All API routes** under `/api/v1/` (see `config/api_urls.py`). Admin panel at `/backstage/`
- **Apps** in `apps/`: contacts, gifts, tasks, journals, groups, events, imports, dashboard, insights, users, core, prayers
- **Base model**: `apps/core/models.TimeStampedModel` — UUID PK, `created_at`, `updated_at`. All models inherit from this.
- **Money is stored in cents** as `PositiveBigIntegerField`, never Decimal. Fields named `*_cents`.
- **Owner-scoped data**: Most models have an `owner` FK to User. Query-level scoping uses `get_visible_user_ids(user, request)` from `apps/core/permissions.py` — returns a set of user IDs or `None` (meaning "all"). This is the central data-scoping choke point.
- **Signals**: `apps/gifts/signals.py` updates denormalized contact stats (total_given, gift_count, last_gift_date) on gift save/delete.
- **CSV imports**: Idempotent upserts via external ID fields. `StreamingHttpResponse` generators for exports (errors are silently swallowed in generators).
- **View As**: Admin/supervisor can scope API requests to another user via `X-View-As-User-Id` header, handled by middleware setting `request.view_as_user`.

### Frontend
- **React 19 + TypeScript + Vite**. Path alias `@/` maps to `frontend/src/`.
- **Provider hierarchy**: ThemeProvider > ErrorBoundary > QueryProvider > AuthProvider > ViewAsProvider > BrowserRouter > NuqsAdapter
- **State**: React Query v5 for server state (global `staleTime: 5min`). No Redux/Zustand. URL filter state via nuqs.
- **API layer**: `frontend/src/api/client.ts` (axios with JWT interceptor + token refresh). Per-resource modules in `api/` export typed async functions. Hooks in `hooks/` wrap React Query.
- **UI**: shadcn/ui (Radix primitives) + Tailwind CSS. Heavy pages (Dashboard, charts, JournalDetail) are lazy-loaded.
- **Filter pattern**: `useFilterParams` hook (wraps nuqs `useQueryStates`) + `FilterBar` component. Pass clean `Record<string, string>` as query keys (no `undefined` values — they cause key collisions via JSON serialization).

### User Roles
Four roles: `admin`, `missionary`, `supervisor`, `coach`. Key permission classes in `apps/core/permissions.py`:
- `IsAdmin` — admin only
- `IsStaffOrAbove` — excludes coach from writes
- `IsOwnerOrAdmin` — object-level owner check
- `get_visible_user_ids()` — determines whose data a user can see

### Test Setup
- pytest with `DJANGO_SETTINGS_MODULE=config.settings.test` (SQLite in-memory, disabled migrations, MD5 hasher)
- Coverage: 80% minimum, scoped to `apps/`, excludes migrations/tests/admin
- Fixtures in `conftest.py`: `api_client`, `authenticated_client` (missionary), `admin_client`, `user_factory`
- User factories in `apps/users/tests/factories.py`

## Key Gotchas
- `User.full_name` is a `@property`, not Django's `get_full_name()` method
- Date-only strings (`"2026-02-01"`) parsed by `new Date()` are UTC midnight, displaying as previous day in US timezones. Use `formatLocalDate()` from `frontend/src/lib/utils.ts`.
- `django-filter` must stay on 24.3 (25.2+ requires Django 5.2). Use individual `DateFilter` fields with `lookup_expr`, not `DateFromToRangeFilter`.
- isort sections: FUTURE > STDLIB > DJANGO > DRF > THIRDPARTY > FIRSTPARTY > LOCALFOLDER (custom `known_django`, `known_drf`, `known_first_party` in pyproject.toml)
- Black line length: 100

### The #1 Rule of E2E Tests A test MUST fail when the feature it tests is broken. No exceptions. If a real user would see something broken, the test must fail. No "fixing the app inside the test". A passing test that hides a broken feature is worse than no test at all.
