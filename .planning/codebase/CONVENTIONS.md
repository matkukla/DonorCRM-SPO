# Coding Conventions

**Analysis Date:** 2026-01-24

## Naming Patterns

**Files:**
- Python files: `snake_case.py` (e.g., `models.py`, `serializers.py`, `views.py`)
- React/TypeScript files: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Test files: `test_*.py` for pytest convention (e.g., `test_models.py`, `test_views.py`)
- Factories: `factories.py` in each app's `tests/` directory

**Functions:**
- Python: `snake_case` (e.g., `get_what_changed()`, `get_dashboard_summary()` in `apps/dashboard/services.py`)
- TypeScript/React: `camelCase` for utility functions (e.g., `getAccessToken()`, `setTokens()` in `frontend/src/api/client.ts`)
- React components: `PascalCase` function names (e.g., `ContactForm()` in `frontend/src/pages/contacts/ContactForm.tsx`)

**Variables:**
- Python: `snake_case` (e.g., `contact_id`, `user_factory` in `apps/contacts/tests/factories.py`)
- TypeScript: `camelCase` (e.g., `formData`, `isEditing` in `frontend/src/pages/contacts/ContactForm.tsx`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `ACCESS_TOKEN_KEY`, `REFRESH_TOKEN_KEY` in `frontend/src/api/client.ts`)

**Types:**
- Django models: `PascalCase` (e.g., `Contact`, `User`, `Pledge` in `apps/contacts/models.py`)
- Serializers: `PascalCase` with `Serializer` suffix (e.g., `ContactListSerializer`, `ContactDetailSerializer` in `apps/contacts/serializers.py`)
- TypeScript interfaces: `PascalCase` with `Props` suffix for component props (e.g., `StatCardProps` in `frontend/src/components/dashboard/StatCard.tsx`)
- Enums: `PascalCase` (e.g., `ContactStatus`, `UserRole` in `apps/contacts/models.py`)

**Django TextChoices:**
- Use `UPPER_CASE` for choice names: `PROSPECT = 'prospect', 'Prospect'` in `apps/contacts/models.py`
- Accessed as enums: `ContactStatus.PROSPECT`, `UserRole.STAFF`

## Code Style

**Formatting:**
- **Python:** Black formatter with 100 character line length (configured in `pyproject.toml`)
  - Target version: Python 3.11
  - Excludes migrations, venv, build directories
- **TypeScript/React:** ESLint with TypeScript support
  - Config: `frontend/eslint.config.js`
  - Uses `typescript-eslint` for TS linting
  - React hooks linting with `eslint-plugin-react-hooks`

**Linting:**
- **Python:**
  - Black: Code formatting to 100 char lines
  - isort: Import organization with Black profile
  - Django and DRF aware sections in isort
  - Strict type checking with mypy rules
- **TypeScript:**
  - ESLint 9.x with strict mode enabled
  - React hooks rules enforced
  - React Refresh plugin for fast refresh during development
  - TypeScript strict mode in `frontend/tsconfig.app.json`

**TypeScript Compiler Settings:**
- Target: ES2022
- Strict mode: Enabled
- `noUnusedLocals`: true - warns on unused variables
- `noUnusedParameters`: true - warns on unused parameters
- `noFallthroughCasesInSwitch`: true
- JSX: react-jsx

## Import Organization

**Python Order (from isort config in `pyproject.toml`):**
1. FUTURE imports
2. STDLIB imports
3. DJANGO imports
4. DRF imports (rest_framework)
5. THIRDPARTY imports
6. FIRSTPARTY imports (apps, config)
7. LOCALFOLDER imports

Example from `apps/contacts/serializers.py`:
```python
from rest_framework import serializers
from apps.contacts.models import Contact, ContactStatus
from apps.groups.serializers import GroupSerializer
```

**TypeScript Path Aliases:**
- Configured in `frontend/tsconfig.app.json`: `"@/*": ["./src/*"]`
- Used consistently in imports (e.g., `@/api/dashboard`, `@/components/ui/card`)

**Import Style Patterns:**
- Type imports in TypeScript: `import type { LucideIcon } from "lucide-react"` in `frontend/src/components/dashboard/StatCard.tsx`
- Destructured imports for utilities and components
- Default exports for page components: `export default function ContactForm()`
- Named exports for utility functions and hooks

## Error Handling

**Patterns:**
- **Python API:** Custom APIException subclasses in `apps/core/exceptions.py`:
  - `DuplicateRecordError` (status 409)
  - `ImportValidationError` (status 400)
  - `PledgeFulfillmentError` (status 400)
- **Django Views:** Try/except blocks with explicit `DoesNotExist` catches (e.g., `Contact.DoesNotExist` in `apps/contacts/views.py`)
  - Return HTTP status codes via Response objects
  - Return 404 for missing resources, 403 for permission issues
- **React Frontend:** Error state in useState hooks
  - Validation errors stored as `Record<string, string>`
  - Form validation clears errors on field change

## Logging

**Framework:** Python uses standard Django logging (not explicitly configured in sample files)

**Patterns:**
- Error messages returned in API responses: `Response({'detail': '...'}, status=...)`
- Django signals used for side effects (e.g., pledge and donation signals in respective apps)
- No logging imports found in sampled code - assume standard Django logging setup

## Comments

**When to Comment:**
- Module docstrings required: All files start with `"""Module description"""`
- Class docstrings: Documented with purpose (e.g., `"""Represents a donor or prospect."""` in `apps/contacts/models.py`)
- Method docstrings for tests: Test methods document their purpose
- Inline comments for complex logic (e.g., token refresh queue logic in `frontend/src/api/client.ts`)

**JSDoc/TSDoc:**
- React component props typed with TypeScript interfaces (no JSDoc required)
- Example: `interface StatCardProps { title: string; value: string | number; ... }`
- Python docstrings follow PEP 257 style with class and method documentation

## Function Design

**Size:**
- Methods are short and focused
- Example: `getAccessToken()` is 3 lines in `frontend/src/api/client.ts`
- Service functions return dict/object with nested data (e.g., `get_dashboard_summary()` returns dict with multiple sections)

**Parameters:**
- **Python:** Use positional args for required, keyword args for optional
  - Serializers accept `instance` and `validated_data`
  - Views use `self.request` to access request context
- **TypeScript:** Props passed as object (e.g., `StatCardProps` interface in `frontend/src/components/dashboard/StatCard.tsx`)

**Return Values:**
- **Python DRF Views:** Return Response objects with data dict or list
- **Python Services:** Return dicts suitable for serialization (JSON-safe)
- **TypeScript Hooks:** Return QueryResult objects from React Query (data, isLoading, error, etc.)
- **React Components:** Render JSX elements

## Module Design

**Exports:**
- **Python:** All model, serializer, and view classes defined in their standard locations per Django convention
  - `models.py` contains all model definitions
  - `serializers.py` contains all serializer classes
  - `views.py` contains all API view classes
- **TypeScript:**
  - Components use `export default function ComponentName()`
  - Utilities use `export const functionName()`
  - Types use `export type InterfaceName = {...}` or `export interface InterfaceName`

**Barrel Files:**
- Not used in this codebase - imports go directly to source files
- Example: `from apps.contacts.serializers import ContactListSerializer` (not from `apps.contacts`)

**Django App Structure:**
- Each feature area has its own app (contacts, donations, pledges, tasks, etc.)
- Standard Django app structure:
  - `models.py` - database models
  - `views.py` - API views
  - `serializers.py` - DRF serializers
  - `urls.py` - URL routing
  - `admin.py` - Django admin configuration
  - `tests/` - test directory with factories and test files
  - `migrations/` - database migrations

## Model Design Patterns

**Django Models:**
- All models inherit from `TimeStampedModel` (custom base in `apps/core/models.py`) providing `created_at` and `updated_at`
- Denormalized fields for performance (e.g., `total_given`, `gift_count` on Contact)
- Proper help_text on model fields for documentation
- Database indexes on frequently queried fields: `db_index=True`
- Composite indexes defined in Meta.indexes (e.g., owner + status in Contact)

**Model Methods:**
- Status transition methods (e.g., `pledge.pause()`, `pledge.resume()`, `pledge.cancel()`)
- Calculation properties (e.g., `pledge.monthly_equivalent`, `pledge.fulfillment_percentage`)
- Business logic methods (e.g., `contact.mark_thanked()`)

## API View Patterns

**Class-based Views:**
- Use DRF generics: `ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`
- Override `get_queryset()` for custom filtering based on user role/ownership
- Override `get_serializer_class()` to use different serializers for different methods
- Use `@extend_schema` decorators for OpenAPI documentation (drf-spectacular)

**Permissions:**
- Always require `permissions.IsAuthenticated` as base
- Add custom permission classes like `IsContactOwnerOrReadAccess`, `IsStaffOrAbove`
- Permission classes combine multiple concerns (ownership + role)

**Query Optimization:**
- Use `select_related()` for foreign keys (e.g., `select_related('owner')`)
- Use `prefetch_related()` for reverse relations
- Filter early in `get_queryset()` to reduce database queries

---

*Convention analysis: 2026-01-24*
