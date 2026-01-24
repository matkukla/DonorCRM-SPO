# Architecture

**Analysis Date:** 2026-01-24

## Pattern Overview

**Overall:** Three-tier REST API with separated backend (Django/DRF) and frontend (React/TypeScript) applications.

**Key Characteristics:**
- Django REST Framework with JWT authentication for API layer
- PostgreSQL with denormalized fields for performance
- Event-driven architecture for state changes via Django signals
- Celery task queue for asynchronous operations (import processing, scheduled checks)
- Role-based access control (RBAC) enforced at permission class level
- Service layer pattern for business logic aggregation
- React SPA with hooks and context providers for state management

## Layers

**Presentation Layer (Frontend):**
- Purpose: Web UI for donor management workflows
- Location: `frontend/src/`
- Contains: React components, pages, hooks, API clients
- Depends on: REST API via `apiClient`
- Used by: End users in browser
- Key files: `App.tsx` (routing), `api/client.ts` (HTTP layer), `providers/` (auth/query)

**API Layer (Django REST Framework):**
- Purpose: HTTP endpoints for all CRUD operations on domain objects
- Location: `config/api_urls.py` (routing), `config/settings/` (configuration)
- Contains: Views (generics/ViewSets), Serializers, URL routing
- Depends on: Domain models, Permission classes, Services
- Used by: Frontend React app, external clients
- Key entry point: `config/urls.py` routes to `config/api_urls.py` which routes to app-specific URLs

**Domain/Business Logic Layer:**
- Purpose: Core domain models and business rules
- Location: `apps/*/models.py`, `apps/*/services.py`
- Contains: Django ORM models with properties/methods, service functions
- Depends on: Database layer
- Used by: Views, Serializers, Tasks, Signals
- Base model: `apps/core/models.TimeStampedModel` (UUID PK, created_at, updated_at)

**Data Layer:**
- Purpose: Database access and persistence
- Location: PostgreSQL (configured in `config/settings/base.py`)
- Contains: ORM models with indexes and constraints
- Depends on: Nothing (bottom layer)
- Used by: All upper layers via Django ORM

**Background Task Layer (Celery):**
- Purpose: Asynchronous job processing
- Location: `apps/*/tasks.py`, `config/celery.py`
- Contains: Shared tasks, beat schedule
- Depends on: Models, Services, Redis broker
- Used by: Views (for large imports), Beat scheduler (periodic checks)
- Configuration: `config/celery.py` defines schedule with crontab times

**Infrastructure/Cross-Cutting Concerns:**
- Purpose: Shared utilities and middleware
- Location: `apps/core/` (permissions, pagination, base models)
- Contains: Permission classes, pagination, email service, exception types
- Depends on: Framework (DRF, Django)
- Used by: Views, Serializers across apps

## Data Flow

**Create Contact Flow:**
1. `POST /api/v1/contacts/` → `ContactListCreateView` (DRF generic)
2. `ContactCreateSerializer` validates and sets `owner=request.user`
3. Contact saved to DB with denormalized stats (total_given=0, gift_count=0)
4. Signal `post_save` fired → creates Event in `apps/events` model
5. Response serialized with `ContactListSerializer` containing nested relationships

**Add Donation Flow:**
1. `POST /api/v1/donations/` → `DonationCreateView`
2. `DonationSerializer` validates amount, date, links to Contact
3. Donation saved with `thanked=False`, triggers donation signal
4. View calls `contact.update_giving_stats()` → recalculates total_given, gift_count, status
5. Contact status auto-upgraded from PROSPECT → DONOR if first gift
6. Signal creates Event: "New donation recorded"
7. If contact.needs_thank_you was True, cleared by this method

**Pledge Late Payment Detection:**
1. Scheduled task `check-late-pledges-daily` runs at 6 AM UTC (defined in `config/celery.py`)
2. Task `apps.pledges.tasks.check_late_pledges` queries pledges with is_late=False
3. For each, calls `pledge.check_late_status(grace_days=10)`
4. If now late: sets is_late=True, days_late=X, creates Event "Pledge payment overdue"
5. User sees late pledges in dashboard via `get_needs_attention()` service

**Dashboard Data Assembly:**
1. `GET /api/v1/dashboard/` → `DashboardView`
2. View calls `get_dashboard_summary(request.user)` from `apps/dashboard/services.py`
3. Service function chains multiple queries:
   - `get_what_changed()`: Filters Events by user
   - `get_needs_attention()`: Late pledges, overdue tasks, thank-you queue
   - `get_at_risk_donors()`: Last gift > 60 days + 2+ prior gifts
   - `get_support_progress()`: Sum of active pledges' monthly_equivalent vs goal
4. Results converted to dicts and returned as JSON
5. Frontend aggregates into card widgets

**Import Processing (Async):**
1. `POST /api/v1/imports/contacts/?async=true` → `ContactImportView`
2. File parsed: `parse_contacts_csv()` validates each row with `ContactImportSerializer`
3. If >50 rows: returns 202 with import_id, queues Celery task `import_contacts_async`
4. Background task: `import_contacts()` bulk creates Contact objects, associates groups
5. View polls `GET /api/v1/imports/{import_id}/` → `get_import_progress()` for status
6. On completion: creates Event "Import finished: 150 contacts added"

**State Management (Frontend):**
1. `AuthProvider` wraps app, stores JWT tokens in localStorage
2. `apiClient` interceptor auto-injects Authorization header
3. On 401: intercepts response, calls `/auth/refresh/` with refresh token
4. If refresh succeeds: queues failed requests with new access token
5. If refresh fails: clears tokens, redirects to `/login`
6. `QueryProvider` (React Query) caches API responses, manages loading/error states

## Key Abstractions

**Contact Ownership Model:**
- Purpose: Multi-tenant isolation of donor data
- Examples: Contact.owner (ForeignKey), Task.owner, Pledge.contact.owner
- Pattern: Views filter by `owner=user` unless user is admin/finance
- Enforced by: `IsContactOwnerOrReadAccess` permission class in `apps/core/permissions.py`

**Permission System:**
- Purpose: Role-based access control
- Examples: `IsAdmin`, `IsStaffOrAbove`, `IsContactOwnerOrReadAccess`
- Location: `apps/core/permissions.py`
- Pattern: Combined in view `permission_classes = [IsAuthenticated, IsStaffOrAbove]`
- User roles: STAFF, ADMIN, FINANCE, READ_ONLY (defined in `apps/users/models.UserRole`)

**Event/Audit Trail:**
- Purpose: Track all state changes for notification and audit
- Examples: Pledge status change → Event created with metadata
- Pattern: Django signals (`@receiver(post_save, sender=Model)`) create events
- Location: `apps/pledges/signals.py`, `apps/donations/signals.py`
- Use case: "Contact marked as thanked" → Event → Dashboard notification

**Denormalized Statistics:**
- Purpose: Optimize query performance for frequently-accessed aggregates
- Examples: Contact.total_given, Contact.gift_count, Pledge.total_received
- Pattern: Updated in model methods (e.g., `contact.update_giving_stats()`)
- Trade-off: Denormalization must be kept in sync via view logic or tasks

**Frequency Calculations:**
- Purpose: Convert pledge frequencies to comparable units
- Examples: Pledge.monthly_equivalent (property)
- Pattern: Use dateutil.relativedelta for date math, multiplication factors for amounts
- Location: `apps/pledges/models.Pledge.monthly_equivalent` property

**Service Layer Pattern:**
- Purpose: Aggregate complex queries and calculations away from views
- Examples: `apps/dashboard/services.py` with functions like `get_support_progress(user)`
- Location: `{app}/services.py` files
- Pattern: Functions take user + optional filters, return dicts ready for serialization
- Benefit: Reusable across multiple view endpoints

## Entry Points

**Backend Entry Point:**
- Location: `manage.py`
- Triggers: `python manage.py runserver` or `gunicorn config.wsgi`
- Responsibilities: Load Django, execute migrations, start HTTP server

**API Entry Point:**
- Location: `config/wsgi.py` and `config/asgi.py`
- Triggers: HTTP requests to `/api/v1/*`
- Responsibilities: Route to appropriate DRF view based on URL pattern

**Frontend Entry Point:**
- Location: `frontend/src/main.tsx`
- Triggers: Browser loads HTML, executes React bundle
- Responsibilities: Mount React app, initialize providers (Auth, Query)

**Background Task Entry Point:**
- Location: `config/celery.py`
- Triggers: `celery -A config worker -l info` or beat schedule
- Responsibilities: Execute queued tasks and periodic checks

**Authentication Entry Point:**
- Location: `apps/users/views_auth.py` (`TokenObtainPairView`)
- Triggers: `POST /api/v1/auth/token/`
- Responsibilities: Validate credentials, return JWT access + refresh tokens

## Error Handling

**Strategy:** Raise custom exceptions with status codes, catch at view level

**Patterns:**

API Layer:
- Views use DRF's `generics` which handle 404, 400, 403 automatically
- Custom exceptions defined in `apps/core/exceptions.py`
- Example: `contact = Contact.objects.get(pk=pk)` → 404 if not found
- View returns Response with error dict and appropriate HTTP status

Signal Handlers:
- Wrapped in try/except to avoid crashing save operations
- Log warnings but don't re-raise (fail silently pattern)
- Example: If Event creation fails, donation still saves

Task Handlers:
- Celery tasks wrapped in logger.info/error calls
- Return string success message or raise for retry
- Long-running tasks have soft/hard limits in settings (5m/10m)

Frontend Layer:
- apiClient interceptor catches all errors
- 401/403 → redirect to login
- 5xx → display toast notification to user
- Failed requests queued for retry on token refresh

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging configured in `config/settings/base.py`
- Pattern: `logger = logging.getLogger(__name__)` in each module
- Levels: DEBUG for apps, INFO for Django, varies by environment

**Validation:**
- DRF Serializers validate all input (field types, max_length, custom validators)
- Database constraints enforced (UniqueConstraint on email per owner, required fields)
- Example: `ContactImportSerializer` in `apps/contacts/serializers.py` line 123

**Authentication:**
- JWT tokens issued by `TokenObtainPairView`, blacklisted on logout
- Token lifetime: 15 min access, 7 day refresh
- Frontend: tokens in localStorage, injected by apiClient interceptor

**Pagination:**
- Standard: 25 items per page (configurable via query_param)
- Large export: 100 items per page
- Implementation: `StandardPagination` class in `apps/core/pagination.py`

**Filtering:**
- DRF FilterBackend chain: DjangoFilterBackend → SearchFilter → OrderingFilter
- Example: `filterset_fields = ['status', 'needs_thank_you']` in ContactListCreateView

**Timezone Handling:**
- Setting: `TIME_ZONE = 'UTC'` in base.py
- Pattern: Use `timezone.now()` from django.utils
- Example: Pledge.check_late_status() compares dates with timezone.now().date()

---

*Architecture analysis: 2026-01-24*
