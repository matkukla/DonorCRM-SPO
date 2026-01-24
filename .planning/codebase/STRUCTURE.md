# Codebase Structure

**Analysis Date:** 2026-01-24

## Directory Layout

```
DonorCRM/
├── config/                 # Django project settings and routing
│   ├── settings/
│   │   ├── base.py        # Shared settings (DB, apps, middleware, logging)
│   │   ├── dev.py         # Development overrides
│   │   ├── prod.py        # Production overrides
│   │   └── test.py        # Test settings
│   ├── api_urls.py        # API v1 routes (all /api/v1/* paths)
│   ├── urls.py            # Root URL routing (admin, /api/v1/, debug toolbar)
│   ├── celery.py          # Celery app config, beat schedule
│   ├── wsgi.py            # WSGI entry point
│   └── asgi.py            # ASGI entry point
├── apps/                   # Django applications (domain + views)
│   ├── core/              # Shared utilities
│   │   ├── models.py      # TimeStampedModel base class
│   │   ├── permissions.py # Permission classes (RBAC)
│   │   ├── pagination.py  # Pagination classes
│   │   ├── email.py       # Email templates
│   │   ├── exceptions.py  # Custom exceptions
│   │   └── management/    # Django management commands
│   ├── users/             # Authentication and user management
│   │   ├── models.py      # User (custom, email-based) with roles
│   │   ├── serializers.py # User serializers
│   │   ├── views.py       # User CRUD endpoints
│   │   ├── views_auth.py  # JWT token endpoints
│   │   ├── managers.py    # Custom UserManager
│   │   ├── urls.py        # /api/v1/users/*
│   │   └── urls_auth.py   # /api/v1/auth/*
│   ├── contacts/          # Donor/prospect management
│   │   ├── models.py      # Contact model (owner, status, giving stats)
│   │   ├── serializers.py # ContactListSerializer, DetailSerializer, etc.
│   │   ├── views.py       # ContactListCreateView, ContactDetailView, etc.
│   │   ├── urls.py        # /api/v1/contacts/*
│   │   ├── tasks.py       # Celery task: detect_at_risk_donors
│   │   └── tests/         # Unit and integration tests
│   ├── donations/         # Gift tracking
│   │   ├── models.py      # Donation model (contact, pledge, amount, date)
│   │   ├── serializers.py # DonationSerializer, DonationCreateSerializer
│   │   ├── views.py       # DonationListCreateView, DonationDetailView
│   │   ├── urls.py        # /api/v1/donations/*
│   │   ├── signals.py     # Signal: donation saved → update contact stats
│   │   └── tests/
│   ├── pledges/           # Recurring giving commitments
│   │   ├── models.py      # Pledge (amount, frequency, status, fulfillment tracking)
│   │   ├── serializers.py # PledgeSerializer
│   │   ├── views.py       # PledgeListCreateView, PledgeDetailView
│   │   ├── urls.py        # /api/v1/pledges/*
│   │   ├── tasks.py       # Celery task: check_late_pledges
│   │   ├── signals.py     # Signal: pledge status change → create Event
│   │   └── tests/
│   ├── tasks/             # Reminders and action items
│   │   ├── models.py      # Task (owner, contact, due_date, status)
│   │   ├── serializers.py # TaskSerializer
│   │   ├── views.py       # TaskListCreateView, TaskDetailView
│   │   ├── urls.py        # /api/v1/tasks/*
│   │   └── tests/
│   ├── groups/            # Contact tags/segments
│   │   ├── models.py      # Group (name, description, many-to-many to Contact)
│   │   ├── serializers.py # GroupSerializer
│   │   ├── views.py       # GroupListCreateView, GroupDetailView
│   │   ├── urls.py        # /api/v1/groups/*
│   │   └── tests/
│   ├── events/            # Audit trail and notifications
│   │   ├── models.py      # Event (user, event_type, title, severity, is_read)
│   │   ├── serializers.py # EventSerializer
│   │   ├── views.py       # EventListView (mark as read)
│   │   ├── urls.py        # /api/v1/events/*
│   │   └── tests/
│   ├── dashboard/         # Aggregated views and reporting
│   │   ├── services.py    # Service functions (get_dashboard_summary, etc.)
│   │   ├── views.py       # DashboardView, AtRiskDonorsView
│   │   ├── tasks.py       # Celery task: generate_weekly_summary
│   │   ├── urls.py        # /api/v1/dashboard/*
│   │   └── tests/
│   └── imports/           # CSV import/export
│       ├── services.py    # parse_contacts_csv, import_contacts, export_donations_csv
│       ├── views.py       # ContactImportView, DonationExportView, etc.
│       ├── tasks.py       # Celery task: import_contacts_async, import_donations_async
│       ├── urls.py        # /api/v1/imports/*
│       └── tests/
├── frontend/              # React TypeScript single-page application
│   ├── src/
│   │   ├── main.tsx       # Entry point: mount React to #root
│   │   ├── App.tsx        # Router config, protected routes, layout
│   │   ├── api/           # API client layer
│   │   │   ├── client.ts  # Axios instance, token management, interceptors
│   │   │   ├── auth.ts    # Login, logout, token refresh
│   │   │   ├── contacts.ts# Contacts CRUD + search
│   │   │   ├── donations.ts
│   │   │   ├── pledges.ts
│   │   │   ├── tasks.ts
│   │   │   ├── groups.ts
│   │   │   ├── imports.ts # Import status polling
│   │   │   ├── dashboard.ts
│   │   │   └── users.ts
│   │   ├── components/    # Reusable React components
│   │   │   ├── auth/      # ProtectedRoute, Login form
│   │   │   ├── layout/    # AppLayout, Navigation, Sidebar
│   │   │   ├── dashboard/ # Dashboard cards and widgets
│   │   │   ├── contacts/  # ContactCard, ContactForm, ContactTable
│   │   │   ├── donations/ # DonationForm, DonationTable
│   │   │   ├── pledges/   # PledgeCard, PledgeForm
│   │   │   ├── shared/    # Modal, Button, Input components
│   │   │   ├── ui/        # Base UI components (reusable, styled)
│   │   │   └── imports/   # ImportProgress, FileUpload
│   │   ├── pages/         # Page-level components (route consumers)
│   │   │   ├── Login.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── contacts/  # ContactList, ContactDetail, ContactForm
│   │   │   ├── donations/
│   │   │   ├── pledges/
│   │   │   ├── tasks/
│   │   │   ├── groups/
│   │   │   ├── settings/
│   │   │   ├── admin/
│   │   │   └── imports/
│   │   ├── hooks/         # Custom React hooks
│   │   │   ├── useAuth.ts # Auth context consumer
│   │   │   ├── useApi.ts  # API error handling
│   │   │   └── ...
│   │   ├── providers/     # Context providers
│   │   │   ├── AuthProvider.tsx # JWT tokens, user data
│   │   │   └── QueryProvider.tsx # React Query client
│   │   ├── lib/           # Utilities
│   │   │   ├── formats.ts # Date/currency formatting
│   │   │   └── validation.ts
│   │   ├── styles/        # Global CSS
│   │   │   └── globals.css
│   │   └── assets/        # Images, fonts
│   ├── public/            # Static assets served as-is
│   ├── index.html         # HTML template with <div id="root">
│   ├── vite.config.ts     # Vite build config
│   └── package.json       # Dependencies, scripts
├── templates/             # Django email templates
│   └── emails/            # HTML email templates
├── requirements/          # Python dependency files
│   ├── base.txt          # Shared dependencies
│   ├── dev.txt           # Development tools
│   └── prod.txt          # Production additions
├── conftest.py           # Pytest fixtures and config
├── pyproject.toml        # Python project config (pytest, black, isort)
├── docker-compose.yml    # Local dev environment (Django, React, Postgres, Redis)
├── Dockerfile            # Development image
├── Dockerfile.prod       # Production image
├── manage.py             # Django CLI
└── .env.example          # Environment variables template
```

## Directory Purposes

**config/:**
- Purpose: Django project configuration, routing, Celery setup
- Contains: Settings files for different environments, URL routing, WSGI/ASGI apps
- Key files: `settings/base.py` (all shared config), `api_urls.py` (API routing)

**apps/:**
- Purpose: Modular Django applications, each domain-driven
- Contains: Models, views, serializers, URLs, tests for each domain area
- Convention: Each app has `models.py`, `serializers.py`, `views.py`, `urls.py`

**apps/core/:**
- Purpose: Shared code across all apps
- Contains: Base model class, permission classes, pagination, exceptions, email
- Not a domain - never import a domain from core, only import core from domains

**apps/contacts/, apps/donations/, apps/pledges/, apps/tasks/, apps/groups/, apps/events/, apps/users/:**
- Purpose: Domain-specific applications
- Each app owns: Models (database schema), Views (HTTP endpoints), Serializers (validation/representation)
- Naming: Models in `models.py`, Views in `views.py`, etc.
- URL structure: Each app's `urls.py` included in `config/api_urls.py`

**apps/dashboard/, apps/imports/:**
- Purpose: Cross-domain operations
- dashboard: Aggregates data from multiple apps (contacts, donations, tasks, etc.)
- imports: Processes CSV data for contacts and donations

**frontend/src/:**
- Purpose: React TypeScript single-page application
- Contains: Components, pages, hooks, API clients, styles
- Entry: `main.tsx` mounts to `index.html#root`
- Routing: `App.tsx` uses React Router with ProtectedRoute wrapper

**frontend/src/api/:**
- Purpose: HTTP client layer
- Pattern: One file per API resource (`contacts.ts`, `donations.ts`, etc.)
- Client: `client.ts` exports configured Axios instance with token injection
- Functions: Typically `getContacts()`, `createContact()`, `updateContact()`, `deleteContact()`

**frontend/src/components/:**
- Purpose: Reusable UI components
- Organization: Grouped by feature (`contacts/`, `donations/`, etc.)
- Pattern: Presentational components (take props, no hooks beyond state)
- Location: Use components in pages

**frontend/src/pages/:**
- Purpose: Route-level components, consumed by App.tsx routes
- Pattern: Each page uses components and calls API via hooks
- Naming: PascalCase matching route path (ContactList, ContactDetail, etc.)

## Key File Locations

**Entry Points:**
- Backend HTTP: `config/wsgi.py`
- Backend CLI: `manage.py`
- Frontend: `frontend/src/main.tsx`
- Celery worker: `config/celery.py` (worker process)
- Celery beat: `config/celery.py` (scheduler)

**Configuration:**
- Django settings: `config/settings/base.py` (shared), `dev.py`, `prod.py`, `test.py`
- Database: Postgres connection in `config/settings/base.py` (DATABASES)
- Celery: `config/celery.py`, beat schedule defined with crontab
- Frontend API URL: `frontend/src/api/client.ts` (import.meta.env.VITE_API_BASE_URL)

**Core Logic:**
- User authentication: `apps/users/models.py` (User model, roles), `views_auth.py` (JWT)
- Contact ownership: `apps/contacts/models.py` (Contact.owner field)
- Dashboard aggregations: `apps/dashboard/services.py` (get_dashboard_summary, etc.)
- Permission system: `apps/core/permissions.py` (IsAdmin, IsContactOwnerOrReadAccess, etc.)

**Testing:**
- Pytest config: `pyproject.toml` (settings in [tool.pytest.ini_options])
- Fixtures: `conftest.py` (root level)
- App tests: `apps/{app}/tests/test_*.py` or `apps/{app}/tests/*_test.py`
- Coverage: Configured in `pyproject.toml`, runs automatically

**Async Tasks:**
- Task definitions: `apps/{app}/tasks.py` (marked with @shared_task)
- Beat schedule: `config/celery.py` (crontab times)
- Async import workers: `apps/imports/tasks.py` (import_contacts_async, etc.)

## Naming Conventions

**Files:**
- Models: `models.py` (one per app, all domain classes)
- Views: `views.py` for most apps, `views_auth.py` for special cases
- Serializers: `serializers.py` (all serializers for an app)
- URLs: `urls.py` (DRF path patterns)
- Tasks: `tasks.py` (Celery @shared_task functions)
- Services: `services.py` (business logic functions)
- Tests: `tests/test_*.py` or `tests/*_test.py`

**Directories:**
- Django apps: lowercase with underscores (`contacts`, `pledges`, `imports`)
- React components: PascalCase directories matching component names
- React pages: PascalCase matching route names (`ContactList`, `DonationForm`)
- Migrations: auto-numbered (`0001_initial.py`, `0002_add_field.py`)

**Classes:**
- Models: PascalCase (`Contact`, `Donation`, `Pledge`)
- Choices: PascalCase + suffix (`ContactStatus`, `DonationType`, `PledgeFrequency`)
- Serializers: `{Model}Serializer` or `{Model}{Purpose}Serializer` (`ContactListSerializer`, `ContactDetailSerializer`)
- Views: `{Model}{Action}View` (`ContactListCreateView`, `ContactDetailView`, `ContactThankView`)
- React components: PascalCase matching file name (`ContactForm`, `DonationTable`)
- Context/Providers: `{Domain}Provider` (`AuthProvider`, `QueryProvider`)

**Functions:**
- Django views: Already handled by class names
- Task functions: snake_case with clear purpose (`detect_at_risk_donors`, `check_late_pledges`)
- Service functions: snake_case, start with verb (`get_dashboard_summary`, `export_contacts_csv`)
- React hooks: Start with `use` (`useAuth`, `useApi`, `useQuery`)
- API client functions: Snake case (`getContacts`, `createContact`, `updateContact`)

**Database Fields:**
- Model fields: snake_case (`first_name`, `last_gift_date`, `needs_thank_you`)
- Foreign keys: Related model name + `_id` for raw DB column (`contact_id`)
- Timestamps: `created_at`, `updated_at` (inherited from TimeStampedModel)
- Status/type enums: Short values in snake_case (`status='active'`, `role='staff'`)

## Where to Add New Code

**New API Endpoint:**
1. Add URL pattern to `apps/{domain}/urls.py`:
   ```python
   path('contacts/<uuid:pk>/action/', ContactActionView.as_view(), name='contact-action')
   ```
2. Create view in `apps/{domain}/views.py`:
   ```python
   class ContactActionView(APIView):
       permission_classes = [IsAuthenticated, IsContactOwnerOrReadAccess]
       def post(self, request, pk):
           ...
   ```
3. Create serializer if needed in `apps/{domain}/serializers.py`
4. Write tests in `apps/{domain}/tests/test_views.py`
5. Update OpenAPI decorators with `@extend_schema()` from `drf_spectacular`

**New React Page:**
1. Create page component at `frontend/src/pages/{Domain}/{PageName}.tsx`
2. Use React Query `useQuery` hook to call API
3. Add route to `frontend/src/App.tsx`:
   ```typescript
   <Route path="/route" element={<ProtectedPage><PageName /></ProtectedPage>} />
   ```
4. Create necessary components in `frontend/src/components/{domain}/`
5. Add API client function in `frontend/src/api/{domain}.ts` if needed

**New Scheduled Task:**
1. Define task in `apps/{domain}/tasks.py`:
   ```python
   @shared_task
   def my_periodic_task():
       ...
   ```
2. Register in beat schedule in `config/celery.py`:
   ```python
   'my-task': {
       'task': 'apps.domain.tasks.my_periodic_task',
       'schedule': crontab(hour=6, minute=0),
   }
   ```
3. Write tests in `apps/{domain}/tests/test_tasks.py`

**New Shared Utility:**
- Core helpers: `apps/core/` (permissions, exceptions, email)
- Service functions: `apps/{domain}/services.py` if domain-specific
- Format utilities: `frontend/src/lib/formats.ts` for frontend

**Utilities:**
- Shared helpers: `apps/core/` (permissions, pagination, email)
- Service functions: `apps/{domain}/services.py` if domain-specific
- Format utilities: `frontend/src/lib/formats.ts` for frontend

## Special Directories

**apps/*/migrations/:**
- Purpose: Django database schema migrations
- Generated: Automatically by `python manage.py makemigrations`
- Committed: Yes, always commit migrations
- Never manually edit, always create new migrations for schema changes

**frontend/dist/:**
- Purpose: Built React application (bundled JavaScript)
- Generated: By `npm run build`
- Committed: No, generated artifact
- Used: Served as static files by backend in production

**frontend/node_modules/:**
- Purpose: npm dependencies
- Generated: By `npm install`
- Committed: No, recreated from package-lock.json
- Managed: Use `npm install` to sync with lock file

**staticfiles/:**
- Purpose: Collected static assets for production
- Generated: By `python manage.py collectstatic`
- Committed: No, generated artifact
- Used: Served by CDN or nginx in production

**.env files:**
- Purpose: Environment-specific configuration
- Files: `.env.example` (committed), `.env` (not committed)
- Pattern: Load with `decouple.config()` in Django settings
- Examples: DATABASE_URL, REDIS_URL, SECRET_KEY, DEBUG

---

*Structure analysis: 2026-01-24*
