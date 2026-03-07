# DonorCRM Architecture

A full-stack missionary support management CRM built with Django REST Framework + React.

## System Overview

```
                                  +-----------------------+
                                  |     Static CDN        |
                                  |  (Render Static Site) |
                                  |  React SPA (Vite)     |
                                  +----------+------------+
                                             |
                                      HTTPS / JSON
                                             |
                                  +----------v------------+
                                  |   Django REST API     |
                                  |  (Render Web Service) |
                                  |  Gunicorn + WSGI      |
                                  +----------+------------+
                                             |
                              +--------------+--------------+
                              |                             |
                    +---------v---------+       +-----------v---------+
                    |   PostgreSQL 15   |       |    Redis 7          |
                    |   (Primary DB)    |       |  (Celery broker)    |
                    +-------------------+       +---------------------+
```

**Frontend**: React 19 SPA served as static assets from a CDN. Communicates with the backend exclusively via JSON REST API calls.

**Backend**: Django 4.2 / DRF application serving all API endpoints under `/api/v1/`. Stateless — uses JWT authentication, no server-side sessions.

**Database**: PostgreSQL with UUID primary keys on all models. All monetary values stored as cents (integer) to avoid floating-point precision issues.

**Background Jobs**: Celery workers with Redis broker for async tasks (email notifications, scheduled cleanup). Currently disabled in production to reduce costs.

---

## Backend Architecture

### Project Layout

```
DonorCRM/
├── manage.py                     # Django entry point
├── config/
│   ├── settings/
│   │   ├── base.py               # Shared settings (all environments)
│   │   ├── dev.py                # Development overrides
│   │   ├── prod.py               # Production overrides
│   │   └── test.py               # Test overrides
│   ├── urls.py                   # Root URL config → /admin/ + /api/v1/
│   ├── api_urls.py               # All API routes grouped under /api/v1/
│   ├── wsgi.py                   # WSGI application
│   └── celery.py                 # Celery app configuration
├── apps/
│   ├── core/                     # Shared utilities
│   │   ├── permissions.py        # Permission classes + visibility helper
│   │   ├── pagination.py         # StandardPagination (25/page, max 100)
│   │   └── models.py             # TimeStampedModel (UUID PK, created/updated)
│   ├── users/                    # Custom User model + auth
│   ├── contacts/                 # Donor/prospect management
│   ├── gifts/                    # One-time + recurring gifts
│   ├── tasks/                    # Reminders and action items
│   ├── events/                   # Audit trail / notification feed
│   ├── groups/                   # Contact tags/segments
│   ├── dashboard/                # Aggregation endpoints
│   ├── imports/                  # CSV import/export (RE, SPO formats)
│   ├── journals/                 # Prospect pipeline tracking
│   ├── prayers/                  # Prayer intentions
│   └── insights/                 # Reporting and analytics
├── requirements/
│   ├── base.txt
│   └── prod.txt
├── Dockerfile.prod
├── docker-compose.yml
└── render.yaml                   # Render PaaS deployment blueprint
```

### App File Convention

Each Django app follows a consistent structure:

```
apps/<app_name>/
├── models.py           # Django models
├── serializers.py      # DRF serializers (list, detail, create variants)
├── views.py            # API views (CBVs using DRF generics)
├── urls.py             # URL routing for this app
├── filters.py          # django-filter FilterSets
├── services.py         # Business logic (if complex)
├── export_views.py     # CSV streaming export endpoints
├── signals.py          # Post-save/delete hooks
├── tasks.py            # Celery async tasks
├── admin.py            # Django admin registration
└── migrations/         # Database migrations
```

### API URL Structure

All endpoints live under `/api/v1/`:

```
/api/v1/health/           → Health check (no auth required)
/api/v1/auth/             → Login, token refresh, logout
/api/v1/users/            → User management (admin-only list/create)
/api/v1/users/me/         → Current user profile

/api/v1/contacts/         → Contacts CRUD + nested sub-resources
/api/v1/contacts/<pk>/donations/
/api/v1/contacts/<pk>/pledges/
/api/v1/contacts/<pk>/tasks/
/api/v1/contacts/<pk>/journals/
/api/v1/contacts/<pk>/prayer-intentions/
/api/v1/contacts/export/csv/

/api/v1/donations/        → Gifts CRUD + export
/api/v1/pledges/          → Recurring gifts CRUD + export
/api/v1/tasks/            → Tasks CRUD + complete/overdue/upcoming
/api/v1/events/           → Notification feed
/api/v1/groups/           → Contact groups/tags
/api/v1/dashboard/        → Dashboard summary, giving, monthly gifts
/api/v1/journals/         → Prospect pipeline journeys
/api/v1/prayers/          → Prayer intentions
/api/v1/insights/         → Analytics and reports
/api/v1/imports/          → CSV import (Raiser's Edge, SPO, MPD)
```

### Authentication

**JWT via `djangorestframework-simplejwt`**

1. Client POSTs credentials to `/api/v1/auth/login/`
2. Backend returns `{access, refresh}` JWT tokens
3. Client sends `Authorization: Bearer <access_token>` on all requests
4. Access token expires after 15 minutes; refresh token after 7 days
5. Refresh tokens rotate on use (old token blacklisted)

All endpoints require authentication by default (`IsAuthenticated`). Unauthenticated access is only allowed on `/health/` and `/schema/`.

### Role-Based Access Control

Five roles with a clear hierarchy:

| Role | See All Data | Write All | Write Own | Admin Pages |
|------|:-----------:|:---------:|:---------:|:-----------:|
| Admin | Yes | Yes | Yes | Yes |
| Mission Supervisor | Own + supervised | No | Yes | No |
| Finance | Yes | No | Yes | No |
| Staff | Own only | No | Yes | No |
| Read Only | Yes | No | No | No |

**Permission classes** (`apps/core/permissions.py`):

- `IsAdmin` — Only admin users
- `IsFinanceOrAdmin` — Finance or admin
- `IsStaffOrAbove` — Staff, finance, admin, mission_supervisor (excludes read_only from writes)
- `IsOwnerOrAdmin` — Object owner or admin (object-level)
- `IsSupervisorWriteRestricted` — Supervisors can read visible data but only write their own
- `ReadOnlyOrAdmin` — Safe methods for all; writes for admin only

**Visibility helper** — the core of data scoping:

```python
def get_visible_user_ids(user):
    """Return set of user IDs whose data this user can see, or None for 'all'."""
    if user.role in ['admin', 'finance', 'read_only']:
        return None  # sentinel for "all users"
    if user.role == 'mission_supervisor':
        ids = set(user.supervised_users.filter(is_active=True).values_list('id', flat=True))
        ids.add(user.id)
        return ids
    return {user.id}  # staff sees only own data
```

Every list view calls this to scope its queryset before applying any filters.

### Data Model

**Core ownership pattern**: Most resources have an `owner` FK to User. Gifts inherit ownership through their contact (`gift.donor_contact.owner`).

```
User
├── role (admin | staff | finance | read_only | mission_supervisor)
├── supervisor (FK to self, nullable) — for mission supervisor hierarchy
├── supervised_users (reverse relation)
├── monthly_goal (decimal)
└── dashboard_layout (JSON — tile order for dashboard DnD)

Contact
├── owner (FK to User) — which staff member manages this donor
├── status (prospect | donor | lapsed | lost)
├── giving stats (denormalized: total_given, gift_count, first/last_gift_date)
├── needs_thank_you (boolean, auto-set by gift signals)
├── groups (M2M to Group)
└── external_id, external_constituent_id (for import idempotency)

Gift
├── donor_contact (FK to Contact)
├── amount_cents (PositiveBigIntegerField — NOT decimal)
├── gift_date (DateField)
├── fund (FK to Fund, nullable)
└── credits (M2M to Solicitor via GiftCredit junction table)

RecurringGift
├── donor_contact (FK to Contact)
├── amount_cents (per-installment amount in cents)
├── frequency (monthly | quarterly | semi_annually | annually | etc.)
├── status (active | held | completed | cancelled | terminated)
└── credits (M2M to Solicitor via RecurringGiftCredit)

Task
├── owner (FK to User)
├── contact (FK to Contact, nullable)
├── task_type (call | email | thank_you | meeting | follow_up | other)
├── priority (low | medium | high | urgent)
├── status (pending | in_progress | completed | cancelled)
└── due_date, completed_at, completed_by

Journal (prospect pipeline)
├── owner (FK to User)
├── name, status, stage_type
└── members (M2M to Contact via JournalContact)

Event (audit trail / notifications)
├── user (FK to User) — who sees it
├── event_type, severity, title, message
├── content_type + object_id (GenericForeignKey to any model)
└── is_read (boolean)
```

**Key design decisions**:
- **Cents not decimals** for money — avoids floating-point precision bugs
- **Denormalized contact stats** — `total_given`, `gift_count`, etc. updated by signals on gift save/delete for fast dashboard queries
- **UUID primary keys** on all models via the shared `TimeStampedModel` base class
- **External IDs** with unique constraints for idempotent CSV imports from Raiser's Edge and SPO

### Filtering

Uses `django-filter` v24.3 with individual filter fields:

```python
class ContactFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    needs_thank_you = django_filters.BooleanFilter()
    last_gift_after = django_filters.DateFilter(field_name='last_gift_date', lookup_expr='gte')
    last_gift_before = django_filters.DateFilter(field_name='last_gift_date', lookup_expr='lte')
    group = django_filters.CharFilter(field_name='groups__id')
    owner = django_filters.UUIDFilter(field_name='owner_id')
```

Views combine this with DRF's `SearchFilter` and `OrderingFilter`:

```
GET /api/v1/contacts/?status=donor&search=John&ordering=-total_given&owner=<uuid>
```

### CSV Export

Uses `StreamingHttpResponse` with generator functions to handle large datasets without loading everything into memory:

```python
def get(self, request):
    queryset = self.get_filtered_queryset(request)  # same filters as list view
    def generate():
        yield header_row
        for obj in queryset.iterator():
            yield data_row(obj)
    response = StreamingHttpResponse(generate(), content_type='text/csv')
    return response
```

All string values are sanitized against CSV formula injection (`=`, `+`, `@`, `-` prefixes).

### Services Layer

Complex business logic lives in `services.py` files, separate from views:

- **Dashboard services** (`apps/dashboard/services.py`) — aggregation queries for support progress, giving summaries, monthly gift charts. Uses SQL `CASE/WHEN` for recurring gift frequency normalization rather than Python loops.
- **Import services** (`apps/imports/services.py`) — CSV parsing, validation, and idempotent upsert logic for Raiser's Edge and SPO formats.
- **Insights services** (`apps/insights/services.py`) — reporting queries with role-scoped data access.

### Signals

Gift signals (`apps/gifts/signals.py`) auto-update contact stats and create audit events:

```python
@receiver(post_save, sender=Gift)
def update_contact_stats_on_gift_save(sender, instance, created, **kwargs):
    instance.donor_contact.update_giving_stats()
    if created:
        instance.donor_contact.needs_thank_you = True
        Event.objects.create(...)
```

Signals can be temporarily disabled during bulk imports via `disable_gift_signals()` / `enable_gift_signals()` using thread-local state.

---

## Frontend Architecture

### Technology Stack

- **React 19** with TypeScript (strict mode)
- **Vite** for bundling and dev server
- **React Router v6** for client-side routing
- **React Query v5** (`@tanstack/react-query`) for server state
- **nuqs** for URL-synced filter state
- **shadcn/ui** (Radix UI primitives) for component library
- **Tailwind CSS** with custom SPO design tokens
- **Axios** for HTTP requests
- **dnd-kit** for drag-and-drop dashboard tiles
- **Recharts** for charts (lazy-loaded)
- **Sonner** for toast notifications

### Project Layout

```
frontend/src/
├── main.tsx                      # React entry point
├── App.tsx                       # Routes + provider hierarchy
├── api/
│   ├── client.ts                 # Axios instance, token management, 401 refresh
│   ├── auth.ts                   # Login, logout, getCurrentUser
│   ├── contacts.ts               # Contact CRUD + sub-resource fetches
│   ├── gifts.ts                  # Gifts + recurring gifts
│   ├── dashboard.ts              # Dashboard summary, giving, layout
│   ├── tasks.ts, journals.ts, prayers.ts, etc.
│   └── users.ts                  # User management (admin)
├── providers/
│   ├── AuthProvider.tsx           # Auth context (user, login, logout)
│   ├── QueryProvider.tsx          # React Query client (5min staleTime)
│   └── ThemeProvider.tsx          # Light/dark/system theme
├── hooks/
│   ├── useFilterParams.ts         # URL filter state via nuqs
│   ├── useContacts.ts             # React Query hooks for contacts
│   ├── useGifts.ts                # React Query hooks for gifts
│   ├── useDashboard.ts            # Dashboard layout + data hooks
│   └── use*.ts                    # One hook file per entity
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx          # Sidebar + Header + main content
│   │   ├── Sidebar.tsx            # Navigation with role-based visibility
│   │   └── Header.tsx             # Theme toggle, user dropdown
│   ├── auth/
│   │   └── ProtectedRoute.tsx     # Role-based route guard
│   ├── shared/
│   │   ├── FilterBar.tsx          # Filter controls + badges + export
│   │   ├── DataTable.tsx          # TanStack Table wrapper + pagination
│   │   └── ExportCSVButton.tsx    # CSV download with current filters
│   ├── dashboard/                 # Dashboard tile components
│   └── ui/                        # shadcn/ui primitives (Button, Card, etc.)
├── pages/
│   ├── Dashboard.tsx              # Main dashboard with DnD tiles
│   ├── Login.tsx
│   ├── contacts/                  # ContactList, ContactDetail, ContactForm
│   ├── donations/                 # DonationList, DonationDetail, DonationForm
│   ├── tasks/, journals/, prayers/, pledges/, groups/
│   ├── admin/                     # User management, analytics
│   └── insights/                  # Reporting pages
├── types/                         # Shared TypeScript interfaces
├── lib/
│   ├── utils.ts                   # cn(), formatLocalDate()
│   └── filter-presets.ts          # Preset filter definitions
└── styles/
    └── globals.css                # Tailwind config + SPO design tokens
```

### Provider Hierarchy

Providers wrap the app in this order (outermost first):

```
ThemeProvider           — light/dark/system mode (localStorage)
  ErrorBoundary         — catches render errors
    QueryProvider       — React Query client (5min stale, 1 retry)
      AuthProvider      — user state, login/logout, clears query cache on switch
        BrowserRouter   — React Router
          NuqsAdapter   — URL state sync for filters
            Routes      — page routing
```

### State Management

| What | Where | Why |
|------|-------|-----|
| Server data (contacts, gifts, tasks) | React Query | Auto-caching, refetch, stale management |
| Filters, pagination, search | nuqs (URL query params) | Browser back/forward, shareable URLs |
| Auth user, login state | AuthProvider context | Global, needs to be synchronous |
| Theme preference | ThemeProvider context | Persisted to localStorage |
| Form inputs, UI toggles | React useState | Local, ephemeral |

There is no Redux, Zustand, or other global store. React Query + URL state + Context covers all needs.

### API Client

`frontend/src/api/client.ts` creates a single Axios instance with:

1. **Base URL** from `VITE_API_BASE_URL` env var (defaults to `localhost:8000/api/v1`)
2. **Request interceptor** — attaches `Authorization: Bearer <token>` header
3. **Response interceptor** — on 401, silently refreshes the access token using the refresh token, queues concurrent requests, replays them with the new token. If refresh fails, clears tokens and redirects to `/login`.

### API Module Pattern

Each entity has an API module exporting:
- TypeScript interfaces for request/response shapes
- Pure async functions that call `apiClient.get/post/patch/delete`
- Label maps for enum display values

```typescript
// api/contacts.ts
export interface Contact { id: string; first_name: string; ... }
export async function getContacts(params: Record<string, string>): Promise<PaginatedResponse<Contact>> {
  const response = await apiClient.get("/contacts/", { params })
  return response.data
}
```

### Hook Pattern

Each entity has a hooks file wrapping API calls in React Query:

```typescript
// hooks/useContacts.ts
export function useContacts(params: Record<string, string>) {
  return useQuery({ queryKey: ["contacts", params], queryFn: () => getContacts(params) })
}
export function useCreateContact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createContact,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}
```

Mutations invalidate related query keys in cascade (e.g., creating a gift invalidates `["gifts"]`, `["contacts"]`, and `["dashboard"]`).

### Filter System

URL-synced filters using `nuqs`:

```typescript
// hooks/useFilterParams.ts
const contactFilterParsers = {
  page: parseAsInteger.withDefault(1),
  search: parseAsString,
  status: parseAsString,
  owner: parseAsString,
  // ...
}

// In a list page:
const { filters, setFilters, clearAll, toQueryParams } = useFilterParams(contactFilterParsers)
const { data } = useContacts(toQueryParams())
```

`toQueryParams()` returns a clean `Record<string, string>` with only non-null values — critical for React Query cache key stability.

### List Page Pattern

Every list page follows the same structure:

```
Header (title + "New" button)
FilterBar (search + dropdowns + active badges + clear all + CSV export)
DataTable (paginated, sortable, clickable rows → navigate to detail)
```

Columns are defined with TanStack Table's `ColumnDef<T>[]`, with conditional columns (e.g., Owner column only shown for admin/supervisor).

### Dashboard

The dashboard uses a tile-based layout with drag-and-drop reordering:

- **10 tiles** with fixed size mapping (1-column or 2-column span)
- **dnd-kit** with `rectSortingStrategy` for grid-aware sorting
- **Layout persistence** — tile order saved to `user.dashboard_layout.tile_order` in the database, debounced 1 second after drag
- **Supervisor viewing** — admin/supervisor can select a missionary from a dropdown to view their dashboard in read-only mode (no drag, no markEventsSeen)

### Role Hierarchy (Frontend)

```typescript
const roleHierarchy = { admin: 5, mission_supervisor: 4, finance: 3, staff: 2, read_only: 1 }
```

Used by `ProtectedRoute` and `Sidebar` to determine page access. Supervisor (level 4) cannot see admin pages (level 5), but can see all pages accessible to finance/staff/read_only.

### Styling

**Tailwind CSS** with a custom SPO (St. Paul's Outreach) design system:

- **Primary**: SPO Red `#F04763` (CTAs and highlights)
- **Brand text/borders**: SPO Blue `#3A4D75`
- **Border radius**: `0.75rem` (rounded, not pill-shaped)
- **Dark mode**: Navy backgrounds with near-white text, toggleable via ThemeProvider

The `cn()` utility merges Tailwind classes using `clsx` + `tailwind-merge`.

---

## Deployment

### Production (Render)

Defined in `render.yaml`:

- **Frontend**: Static site built with `npx vite build`, served from CDN with SPA rewrites
- **Backend**: Python web service with Gunicorn, auto-deploys on push to main
- **Database**: Render-managed PostgreSQL
- **Build**: `pip install → collectstatic → migrate` on each deploy

### Development (Docker Compose)

```bash
docker-compose up  # Starts PostgreSQL, Redis, Django, Celery worker, Celery beat
```

Or run locally:
```bash
# Backend
python manage.py runserver

# Frontend
cd frontend && npm run dev
```

### Environment Variables

Key variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key |
| `DB_NAME/USER/PASSWORD/HOST/PORT` | PostgreSQL connection |
| `REDIS_URL` | Celery broker |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s) |
| `VITE_API_BASE_URL` | Backend API URL for frontend |
| `SENTRY_DSN` | Error tracking (production) |

---

## Key Design Decisions

1. **JWT over sessions** — stateless auth, better for SPA clients
2. **Cents not decimals** — `amount_cents: PositiveBigIntegerField` avoids float precision bugs
3. **Owner scoping at query level** — every list view filters by ownership before any other logic
4. **Denormalized contact stats** — `total_given`, `gift_count` updated by signals for fast reads
5. **SQL aggregation over Python** — dashboard uses `CASE/WHEN` for frequency normalization
6. **Streaming CSV exports** — generator pattern prevents memory explosion on large datasets
7. **URL-synced filters** — nuqs keeps filter state in URL params for shareable/bookmarkable views
8. **React Query as primary state** — no Redux/Zustand; server state cached and invalidated
9. **5-level role hierarchy** — admin > supervisor > finance > staff > read_only with centralized visibility helper
10. **External IDs for idempotency** — safe re-imports from Raiser's Edge and SPO systems
