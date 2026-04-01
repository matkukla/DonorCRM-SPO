# claude.md

This file is read by Claude Code at the start of every session. It is the primary context source for AI-assisted development.

## Project Overview

DonorCRM is a purpose-built CRM for missionaries and nonprofit fundraisers at Saint Paul's Outreach (SPO). It tracks gifts, manages recurring pledges, maintains donor relationships, and provides leadership with cross-missionary analytics. Tech stack: Django 4.2 DRF + React 19/TypeScript + PostgreSQL on Render.

## Repo Structure

```
DonorCRM/
├── apps/                  # Django apps (contacts, gifts, tasks, journals, groups, events, imports, dashboard, insights, users, core, prayers)
├── config/                # Django settings (base/dev/test/prod), urls, wsgi, celery
├── frontend/src/
│   ├── api/               # Typed API client functions (one file per resource)
│   ├── hooks/             # React Query hooks (one file per resource)
│   ├── pages/             # Route-level components
│   ├── components/        # Shared + feature-specific UI components
│   ├── providers/         # Auth, Query, Theme, ViewAs context providers
│   └── lib/utils.ts       # formatLocalDate, cn, toQueryParams
├── requirements/          # Python deps (base.txt, dev.txt, prod.txt)
└── render.yaml            # Render deployment blueprint
```

## Architecture Principles — MUST FOLLOW

- Treat this document and SYSTEM_README.md as the primary context source
- Preserve existing architecture unless a redesign is explicitly requested
- Prefer incremental, safe changes over broad refactors
- Do not make up implementation details — if uncertain, read the code first
- If code reality differs from what a prompt assumes, explain the difference and adapt
- Always consider downstream effects, not just the immediate change
- Always preserve contact ownership as the primary data visibility boundary
- Always preserve View As as read-only (mutations blocked by middleware)
- Always preserve coach financial data restriction
- Money is always stored in integer cents (`PositiveBigIntegerField`) — multiply by 100 before storing, divide by 100 before displaying
- All models use UUID primary keys via `TimeStampedModel`
- Date-only strings must use `formatLocalDate()` on the frontend — never raw `new Date()` for date-only values
- React Query keys must be clean objects — use `toQueryParams()` to strip `undefined` values
- django-filter must stay pinned at 24.3 — do not upgrade

## Data Model Rules

- `Contact.owner` is the primary data isolation boundary — all dashboard calculations, analytics, and permission checks flow from this
- Gift credit splitting: Gift → GiftCredit → Solicitor → User
- Dashboard scopes to `donor_contact__owner=user`, NOT `get_visible_user_ids()`
- `get_visible_user_ids()` is for list views and exports, not dashboard calculations
- Denormalized contact stats (total_given, gift_count, first/last_gift_date) updated by signals on gift save/delete
- Money fields: `amount_cents`, `monthly_support_goal_cents` — all `PositiveBigIntegerField`

## Permission Model

### Active Roles (4)

| Role | See | Do | Notes |
|------|-----|-----|-------|
| **missionary** | Own data only | Full CRUD on own data | Default role |
| **admin** | All data | Everything + user management, imports | View As any missionary (read-only) |
| **supervisor** | Own + supervised (via View As) | Full CRUD on own data | Can only view-as assigned missionaries |
| **coach** | Own + coached users (no financial data) | Full CRUD on own data | `is_financial_role()` returns False for coach |

### Deprecated Roles — do NOT build for these
- `finance` — being phased out
- `read_only` — being phased out

### Permission Enforcement Points

| Layer | Mechanism | Location |
|-------|-----------|----------|
| API view | DRF permission classes (`IsAdmin`, `IsStaffOrAbove`, `IsOwnerOrAdmin`) | `apps/*/views.py` |
| Data scoping | `get_visible_user_ids(user, request)` → set of IDs or None | `apps/core/permissions.py` |
| View As | `ViewAsMiddleware` validates header, blocks mutations | `apps/core/middleware.py` |
| Frontend route | `ProtectedRoute` with `requiredRole` prop | `App.tsx` |
| UI hiding | `isViewingAs` context hides create/edit buttons | Various components |

## Common Commands

```bash
# Backend
source venv/bin/activate
python manage.py runserver                    # Dev server on :8000
pytest                                        # Full test suite (SQLite in-memory)
pytest apps/contacts/tests/test_views.py -k "test_list"  # Single test
pytest -m "not slow"                          # Skip slow tests
python manage.py makemigrations && python manage.py migrate
black apps/ config/ && isort apps/ config/    # Format
black --check apps/ config/ && isort --check-only apps/ config/ && flake8 apps/ config/  # Lint

# Frontend
cd frontend
npm run dev                                   # Vite dev server on :5173
npm run build                                 # TypeScript check + Vite build
npm run lint                                  # ESLint

# Docker
docker compose up -d db redis                 # Start Postgres + Redis
docker compose up --build                     # Full stack

# Key management commands
python manage.py create_test_accounts         # Seed test users
python manage.py link_solicitors_and_reassign_owners  # Fix contact ownership after import
python manage.py audit_import_health          # Audit import data health
python manage.py set_missionary_goals         # Set per-missionary goal amounts
python manage.py sync_solicitor_accounts      # Sync solicitors with user accounts
python manage.py import_re_constituents <file> --owner <email>  # RE import
python manage.py import_re_gifts <file> --owner <email>
python manage.py import_re_solicitors <file> --owner <email>
python manage.py import_re_recurring_gifts <file> --owner <email>
```

Deployment: auto-deploy from GitHub to Render. Frontend = static site, Backend = web service, DB = managed Postgres.

## Modification Patterns

### Add a field to an existing model
1. `apps/<app>/models.py` — add field
2. `python manage.py makemigrations` + `migrate`
3. `apps/<app>/serializers.py` — add to fields list
4. `apps/<app>/filters.py` — add filter if needed
5. `frontend/src/api/<resource>.ts` — update TypeScript type
6. `frontend/src/pages/<resource>/` — update form + detail components

### Add a new feature (full stack)
1. Model → migration → serializer → view → URL → permissions
2. API client function → React Query hook → page component → route → sidebar

### Add a dashboard tile
1. Component in `frontend/src/components/dashboard/`
2. Add tile ID to `DEFAULT_TILE_ORDER` in `hooks/useDashboard.ts`
3. Add case to tile renderer in `pages/Dashboard.tsx`
4. Backend: endpoint in `dashboard/views.py` + service in `dashboard/services.py`

### Add an import type
1. Header alias map + parsing in `apps/imports/re_services.py`
2. Management command in `apps/imports/management/commands/`
3. View endpoint in `apps/imports/views.py` + URL
4. Frontend section in `components/imports/`

## Known Gotchas

- **django-filter version pin**: Must stay on 24.3. Version 25.2+ requires Django 5.2. Use individual `DateFilter` fields with `lookup_expr`, not `DateFromToRangeFilter`
- **UTC date display bug**: `new Date("2026-02-01")` = UTC midnight = Jan 31 in US timezones. Always use `formatLocalDate()` from `lib/utils.ts`
- **React Query staleTime**: Global 5-min. Query keys must be clean `Record<string, string>` — `undefined` values cause key collisions via JSON serialization
- **StreamingHttpResponse generators**: Silently swallow exceptions. If CSV export has headers but no data rows, check the generator for runtime errors
- **Import order**: Solicitors → Constituents → Gifts → Recurring Gifts → Smartsheet MPD
- **Contact ownership during import**: If solicitor names don't match, contacts default to admin. Run `link_solicitors_and_reassign_owners` to fix
- **`User.full_name`**: Is a `@property`, not Django's `get_full_name()` method
- **isort sections**: FUTURE > STDLIB > DJANGO > DRF > THIRDPARTY > FIRSTPARTY > LOCALFOLDER (custom known sections in pyproject.toml)
- **Black line length**: 100
- **Admin panel**: at `/admin/` (Django admin)
- **View As blocks mutations**: Middleware returns 403 on POST/PUT/PATCH/DELETE when `X-View-As-User-Id` header is set
- **Dashboard percentage**: Sensitive to `monthly_support_goal_cents` being realistic relative to actual recurring amounts
- **Celery/Redis disabled in production**: All operations are synchronous

## Regression Checklist

After any change, verify:

- [ ] Permissions behave correctly for all 4 active roles (missionary, admin, supervisor, coach)
- [ ] View As remains read-only and properly scoped
- [ ] Dashboard calculations reflect correct contact ownership (`donor_contact__owner=user`)
- [ ] React Query invalidation refreshes affected views
- [ ] Money stays in integer cents backend, dollars frontend
- [ ] Date-only values display correctly in local time
- [ ] Filters, exports, and detail pages still work
- [ ] Coach cannot see financial data (gifts, pledges, amounts)
