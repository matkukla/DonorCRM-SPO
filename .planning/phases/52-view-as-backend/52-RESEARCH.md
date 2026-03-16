# Phase 52: View As — Backend - Research

**Researched:** 2026-03-16
**Domain:** Django middleware, DRF permissions, request scoping
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Middleware placement**
- Django middleware in `apps/core/middleware.py` (not a DRF permission class)
- Sits in the MIDDLEWARE stack; attaches validated target User object to `request.view_as_user`
- Blocks mutations (POST, PUT, PATCH, DELETE) globally before DRF even sees the request
- Zero per-view changes needed — all views benefit automatically

**get_visible_user_ids() update**
- Updated in Phase 52 (not deferred to Phase 53)
- Signature change: accepts optional `request` parameter so it can read `request.view_as_user`
- When `request.view_as_user` is set: returns `{view_as_user.id}` regardless of viewer role
- All callers (contacts, gifts, journals, tasks, prayers, groups, events, dashboard, insights) pick up data scoping automatically through the existing call sites

**Who can use the header**
- Admin and supervisor roles only — any other role sending the header gets a 403
- Target user must be role='missionary' and is_active=True
- Admin: can view any active missionary
- Supervisor: can only view missionaries in their `supervised_users` M2M relation

**Invalid/unauthorized header handling**
- Non-existent user ID → 403 Forbidden
- Target user not in viewer's permitted set → 403 Forbidden
- Viewer role is not admin or supervisor → 403 Forbidden
- All cases use HTTP 403 (not 400) — treats bad header values as a permission violation

**Error response shape**
- Simple `{"detail": "..."}` string format — matches DRF default 403 format used throughout the codebase
- Distinct messages per failure case:
  - Mutation blocked: `"Mutations are not allowed in View As mode."`
  - Unauthorized viewer or target not in permitted set: `"You do not have permission to view as this user."`
  - Target user not found or inactive: `"Invalid View As target."`

**GET /api/users/viewable endpoint**
- URL: `/api/users/viewable/` inside the existing users app URLs
- Consistent with `/api/users/me/` and `/api/users/admin/assignments/`
- Permission: authenticated + (admin or supervisor)
- Admin: returns all active missionaries (role='missionary', is_active=True)
- Supervisor: returns only their `supervised_users` filtered to role='missionary' and is_active=True
- Response shape: `[{"id": "uuid", "full_name": "Jane Doe"}, ...]` — minimal, no sensitive data
- New minimal serializer (not UserSerializer) to avoid oversharing

### Claude's Discretion
- Exact position of the new middleware in the MIDDLEWARE list (after authentication)
- Whether to add a unit test for the middleware directly or test via view-level integration tests
- Naming of the middleware class (e.g., ViewAsMiddleware)
- Whether get_visible_user_ids() receives the full request or just view_as_user as a keyword arg

### Deferred Ideas (OUT OF SCOPE)
- Coach View As support (view their coached missionaries) — deferred to v2.4+ per VIEWAS-EX-01
- Audit log of View As sessions (who viewed whom and when) — deferred to v2.4+ per VIEWAS-EX-02
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEWAS-07 | Backend enforces read-only: mutations return 403 when `X-View-As-User-Id` header is present | ViewAsMiddleware blocks POST/PUT/PATCH/DELETE before DRF routing; returns `{"detail": "Mutations are not allowed in View As mode."}` |
| VIEWAS-08 | Backend validates viewer has permission before allowing View As (admin → any missionary; supervisor → assigned only) | Middleware validates role, target existence/active/role, and M2M membership for supervisors; 403 on all violations |
| VIEWAS-12 | GET /api/users/viewable returns the correct list of users per role (admin → all missionaries; supervisor → assigned only) | New ViewableUsersView with ViewableUserSerializer; queries `supervised_users` M2M for supervisor, `User.objects.filter(role='missionary', is_active=True)` for admin |
</phase_requirements>

---

## Summary

Phase 52 delivers three tightly coupled backend pieces: a Django middleware that validates and attaches a View As target user, a signature update to `get_visible_user_ids()` that redirects data scoping to that target, and a new `GET /api/users/viewable/` endpoint. Together they satisfy VIEWAS-07 (mutation blocking), VIEWAS-08 (permission validation), and VIEWAS-12 (viewable user list).

The codebase is well-prepared for this phase. `get_visible_user_ids()` is already the single choke point for all list view scoping across 18 call sites. The Phase 51 changes already removed the `None` sentinel for admin/supervisor — those roles now return `{user.id}` like everyone else. Phase 52 slots in one more branch at the top of that function: if a valid `view_as_user` is present on the request, return `{view_as_user.id}` immediately, before any role checks. All 18 call sites work unchanged because they already handle the set-of-IDs return type.

The middleware approach (rather than a DRF permission class) is the right choice here: it intercepts at the WSGI level before DRF authentication resolves, which means mutation blocking is enforced even for routes that don't use standard DRF permission checks. The one ordering constraint is that ViewAsMiddleware must come after `AuthenticationMiddleware` in the stack so that `request.user` is populated when the middleware runs.

**Primary recommendation:** Implement in three discrete tasks — (1) middleware + settings entry, (2) `get_visible_user_ids()` signature update + caller pass-through, (3) `ViewableUsersView` + serializer + URL registration — each independently verifiable.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django middleware | Django 4.2 (project standard) | Request interception, mutation blocking | Only layer that runs before DRF; no per-view changes needed |
| Django REST Framework | Project standard | ViewableUsersView, serializer, 403 responses | Already used everywhere; `Response({"detail": "..."}, status=403)` is the established error pattern |
| `apps.core.permissions` | Internal | `get_visible_user_ids()` — data scoping choke point | Phase 51 already centralized all scoping here |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rest_framework.permissions` | Project standard | `IsSupervisor` permission for ViewableUsersView | New combined permission check: admin OR supervisor |
| `apps.users.tests.factories` | Internal | `AdminUserFactory`, `SupervisorUserFactory`, `UserFactory` | All test scenarios use these; no new factories needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Django middleware | DRF permission class | Permission class runs per-view, requires per-view changes; middleware is truly global |
| Django middleware | DRF authentication class | Authentication classes can't block mutations; only validate identity |
| Full `request` passed to `get_visible_user_ids()` | Just `view_as_user` keyword arg | Passing full request is more flexible for future use; either works since the function only reads `request.view_as_user` |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure

New files:
```
apps/core/middleware.py          # ViewAsMiddleware (new file)
apps/users/views.py              # ViewableUsersView added
apps/users/serializers.py        # ViewableUserSerializer added
```

Modified files:
```
apps/core/permissions.py         # get_visible_user_ids() signature update
apps/users/urls.py               # viewable/ path registered
config/settings/base.py          # MIDDLEWARE list updated
```

Call-site files (signature update only — pass request through):
```
apps/contacts/views.py
apps/contacts/export_views.py
apps/prayers/views.py
apps/dashboard/views.py
apps/dashboard/services.py
apps/events/views.py
apps/insights/services.py
apps/journals/views.py
apps/journals/export_views.py
apps/groups/views.py
apps/gifts/views.py
apps/gifts/export_views.py
apps/tasks/views.py
apps/tasks/export_views.py
```

### Pattern 1: Django Middleware with JsonResponse 403

**What:** A `__call__`-based middleware that reads a request header, validates it, and either sets `request.view_as_user` or returns a short-circuit 403 before the view runs.

**When to use:** Any global cross-cutting concern that must run before DRF routing (mutation blocking, rate limiting, tenant resolution).

**Example:**
```python
# apps/core/middleware.py
import json
from django.http import JsonResponse
from apps.users.models import User


class ViewAsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header_value = request.META.get('HTTP_X_VIEW_AS_USER_ID')

        if header_value:
            # Must have an authenticated user before proceeding
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                # Let DRF handle 401 — don't short-circuit here
                return self.get_response(request)

            error = self._validate_view_as(request, header_value)
            if error:
                return JsonResponse({'detail': error}, status=403)

            # Mutation guard
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                return JsonResponse(
                    {'detail': 'Mutations are not allowed in View As mode.'},
                    status=403
                )

        return self.get_response(request)

    def _validate_view_as(self, request, target_id_str):
        viewer = request.user

        if viewer.role not in ('admin', 'supervisor'):
            return 'You do not have permission to view as this user.'

        try:
            target = User.objects.get(pk=target_id_str, role='missionary', is_active=True)
        except (User.DoesNotExist, ValueError):
            return 'Invalid View As target.'

        if viewer.role == 'supervisor':
            if not viewer.supervised_users.filter(pk=target.pk).exists():
                return 'You do not have permission to view as this user.'

        request.view_as_user = target
        return None  # success
```

### Pattern 2: get_visible_user_ids() with Optional Request

**What:** Check for `request.view_as_user` as the first branch. If present, short-circuit and return the target's ID set. Existing role logic is unchanged below it.

**When to use:** Any function that already uses this signature to scope querysets.

**Example:**
```python
# apps/core/permissions.py
def get_visible_user_ids(user, request=None):
    """Return set of user IDs whose data this user can see, or None for 'all'."""
    # View As override: always scope to the target user's data
    if request is not None:
        view_as_user = getattr(request, 'view_as_user', None)
        if view_as_user is not None:
            return {view_as_user.id}

    if user.role in ['finance', 'read_only']:
        return None
    if user.role == 'coach':
        ids = set(
            user.coached_users
            .filter(is_active=True)
            .values_list('id', flat=True)
        )
        ids.add(user.id)
        return ids
    return {user.id}
```

### Pattern 3: Caller Pass-Through

**What:** All existing callers of `get_visible_user_ids(user)` in views get updated to `get_visible_user_ids(user, request=self.request)` (or `request=request` in service functions that already have `request` in scope). Service functions called without a request (e.g., from Celery tasks) remain unaffected by passing `request=None` (the default).

**When to use:** Every view-level or service-level caller listed in the Architecture section above.

### Pattern 4: ViewableUsersView

**What:** A simple `APIView` that queries active missionaries, filtered by role for supervisors. Returns a minimal list serializer — not the full `UserSerializer` (which exposes role, email, goal_cents, etc.).

**Example:**
```python
# apps/users/serializers.py — new minimal serializer
class ViewableUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name']


# apps/users/views.py — new view
class ViewableUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == 'admin':
            qs = User.objects.filter(role='missionary', is_active=True).order_by('last_name', 'first_name')
        elif user.role == 'supervisor':
            qs = user.supervised_users.filter(role='missionary', is_active=True).order_by('last_name', 'first_name')
        else:
            return Response({'detail': 'You do not have permission to view this list.'}, status=403)
        return Response(ViewableUserSerializer(qs, many=True).data)
```

### Pattern 5: MIDDLEWARE List Ordering

**What:** `ViewAsMiddleware` must come after `AuthenticationMiddleware` so `request.user` exists. It should come before `MessageMiddleware` and `XFrameOptionsMiddleware`. A safe position is immediately after `AuthenticationMiddleware`.

**Example:**
```python
# config/settings/base.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware.ViewAsMiddleware',          # <-- after AuthenticationMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Anti-Patterns to Avoid

- **DRF permission class for mutation blocking:** Permission classes run inside DRF's `dispatch()`, which is per-view. A middleware runs before routing and covers every URL in the project, including admin and any future non-DRF endpoints.
- **Returning 401 for an invalid header:** The locked decision is 403 for all validation failures. 401 means "not authenticated"; this user IS authenticated, they just lack permission to use the header.
- **Modifying the `user_id` claim on the JWT:** Full impersonation via token swap is explicitly out of scope (REQUIREMENTS.md "Out of Scope" table). The header approach is the correct pattern.
- **Adding `view_as_user` checks inside each view:** The middleware sets `request.view_as_user` and `get_visible_user_ids()` reads it. No per-view changes are needed.
- **Skipping the `is_active=True` check on the target:** An inactive missionary must return 403 ("Invalid View As target."), not silently succeed with empty data.
- **Passing `request=self.request` in service functions called without a web request:** Services like `get_support_progress()` are called from goal services, not from views. They should not receive a request parameter. Only view-context callers of `get_visible_user_ids()` are updated.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP 403 JSON response in middleware | Custom exception class or middleware response builder | `django.http.JsonResponse({'detail': '...'}, status=403)` | Already the pattern everywhere; DRF uses `{"detail": "..."}` for all permission failures |
| Permission check for ViewableUsersView | Inline `if user.role not in (...)` only | Inline role check in the view method (acceptable here since it's a custom APIView) | The view already does role branching for query scoping; a combined permission + query in one method is clean and consistent with `AssignmentsView` which uses `IsAdmin` only |
| UUID parsing for the header value | Custom try/except UUID parse | Let `User.objects.get(pk=target_id_str)` handle the ValueError — catch `(User.DoesNotExist, ValueError)` together | Avoids redundant parse step; Django's pk lookup raises ValueError on malformed UUIDs already |

---

## Common Pitfalls

### Pitfall 1: Middleware Runs Before DRF Authentication
**What goes wrong:** `request.user` may be `AnonymousUser` at middleware time if JWT authentication hasn't run yet (DRF authentication runs during view dispatch, not during WSGI middleware).
**Why it happens:** Django's `AuthenticationMiddleware` sets session-based users, but DRF's JWT authentication only runs inside `APIView.dispatch()`.
**How to avoid:** In the middleware, check `request.user.is_authenticated` before validating the header. If the user isn't authenticated yet, pass through to `get_response(request)` — DRF will return 401 naturally.
**Warning signs:** Tests that send the header without a valid JWT token cause `AttributeError: 'AnonymousUser' object has no attribute 'role'`.

### Pitfall 2: Supervisor's supervised_users Only Returns Missionaries by M2M — Role Filter Still Needed
**What goes wrong:** The `supervised_users` M2M relation can technically hold any role if admin manually creates unusual assignments. The viewable endpoint and the middleware permission check must both add `.filter(role='missionary', is_active=True)`.
**Why it happens:** The M2M relation is `User → supervised_users → User` with no database constraint on the target role.
**How to avoid:** Always add `.filter(role='missionary', is_active=True)` when querying `supervised_users` for View As purposes.

### Pitfall 3: get_visible_user_ids() Call Sites in Service Functions Without Request
**What goes wrong:** `dashboard/services.py` functions are called both from views (with a request) and potentially from Celery tasks or tests (without). Passing `request=self.request` through service function signatures could cause failures in the non-view context.
**Why it happens:** Services are not views — they don't always have a request.
**How to avoid:** Only view-level callers pass `request=self.request`. Service functions like `get_needs_attention(user)`, `get_mpd_overview()` that are called from views receive the request via the view's caller — specifically, update the view call site, not the service function signature. For services that are called with a user only (no request), pass `request=None` explicitly or leave as default.

### Pitfall 4: Header Name in Django META
**What goes wrong:** HTTP header `X-View-As-User-Id` is accessed as `request.META['HTTP_X_VIEW_AS_USER_ID']` in Django (uppercase, hyphens → underscores, `HTTP_` prefix).
**Why it happens:** Django normalizes all custom HTTP headers this way.
**How to avoid:** Use `request.META.get('HTTP_X_VIEW_AS_USER_ID')` in the middleware. In tests, set it as `HTTP_X_VIEW_AS_USER_ID` in `client.get(..., HTTP_X_VIEW_AS_USER_ID=str(target.id))`.

### Pitfall 5: ViewableUsersView Returns Serializer-Derived IDs as Strings vs UUIDs
**What goes wrong:** If `ViewableUserSerializer` does not override `id` as `serializers.UUIDField()`, the UUID is serialized as a Python UUID object which DRF renders as a string but the test assertion may compare `UUID('...')` vs `'...'`.
**Why it happens:** `ModelSerializer` default UUID field handling.
**How to avoid:** Use `id = serializers.UUIDField(read_only=True)` explicitly, or verify against `str(target.id)` in tests. The existing `AssignmentsView` uses `str(u.id)` manually — the new serializer approach is cleaner but confirm the output format.

---

## Code Examples

Verified patterns from existing codebase:

### Existing 403 pattern (from apps/users/views_assignments.py)
```python
# Source: apps/users/views_assignments.py line 48
return Response({'detail': 'assignments must be a list'}, status=400)
# Same pattern for 403 throughout the codebase
return Response({'detail': 'Not found or not a missionary'}, status=403)
```

### Existing get_visible_user_ids caller pattern (from apps/contacts/views.py)
```python
# Source: apps/contacts/views.py lines 64-68
visible = get_visible_user_ids(user)
if visible is None:
    queryset = Contact.objects.all()
else:
    queryset = Contact.objects.filter(owner_id__in=visible)
```
After Phase 52, this becomes `get_visible_user_ids(user, request=self.request)` — body unchanged.

### Existing AssignmentsView role-check-in-view pattern (from apps/users/views_assignments.py)
```python
# Source: apps/users/views_assignments.py — IsAdmin permission class
permission_classes = [IsAdmin]
```
ViewableUsersView uses the same pattern but needs admin OR supervisor — inline role check in `get()` is cleaner than creating a new combined permission class.

### Existing supervised_users query pattern (from apps/users/serializers.py)
```python
# Source: apps/users/serializers.py lines 207-214
if obj.role == 'supervisor':
    qs = obj.supervised_users.filter(is_active=True)
```
Phase 52 adds `.filter(role='missionary', is_active=True)` to this pattern for security.

### Django middleware __call__ pattern
```python
# Standard Django middleware pattern (Django 4.2 docs)
class SomeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code here runs BEFORE the view
        response = self.get_response(request)
        # Code here runs AFTER the view
        return response
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `get_visible_user_ids()` returns `None` for admin/supervisor | Returns `{user.id}` for admin/supervisor | Phase 51 | The `None` sentinel is now only used for finance/read_only; all other roles return a set of IDs |
| Admin/supervisor could see all missionaries' data by default | Admin/supervisor see only own data by default | Phase 51 | Cross-user access ONLY activates via View As (Phase 52) |

**Deprecated/outdated:**
- `None` return value from `get_visible_user_ids()` for admin/supervisor: Removed in Phase 51. The `if visible is None: queryset = all()` branch in call sites is now only reached by finance/read_only roles. Phase 52 must NOT re-introduce `None` for the view_as_user path.

---

## Open Questions

1. **Should `get_visible_user_ids()` receive `request` or just `view_as_user`?**
   - What we know: CONTEXT.md lists this as Claude's Discretion. Both work since the function only reads `request.view_as_user`.
   - What's unclear: Passing the full request is a larger API surface; passing only `view_as_user` is a more minimal interface.
   - Recommendation: Pass `request=None` (full request, optional). This is more consistent with Django conventions and allows future extensions (e.g., reading other headers) without another signature change. Call sites pass `request=self.request`.

2. **How to handle the case where ViewAsMiddleware runs before JWT authentication resolves `request.user`?**
   - What we know: DRF JWT auth runs inside `APIView.dispatch()`, not during WSGI middleware. `request.user` at middleware time is the session user (AnonymousUser for JWT-only endpoints).
   - What's unclear: Whether to short-circuit or pass through when unauthenticated.
   - Recommendation: If `request.user` is not authenticated, call `get_response(request)` unchanged. DRF will return 401. The middleware only acts on the header when `request.user.is_authenticated` is True. This matches the pattern used in other Django middleware that wrap DRF endpoints.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest apps/core/tests/test_middleware.py apps/users/tests/test_views_viewable.py -x` |
| Full suite command | `pytest --cov=apps --cov-fail-under=80` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIEWAS-07 | POST/PUT/PATCH/DELETE with header returns 403 | integration | `pytest apps/core/tests/test_middleware.py::test_mutation_blocked_* -x` | Wave 0 |
| VIEWAS-07 | GET with header does NOT block | integration | `pytest apps/core/tests/test_middleware.py::test_get_allowed_in_view_as -x` | Wave 0 |
| VIEWAS-08 | Non-admin/supervisor sending header gets 403 | integration | `pytest apps/core/tests/test_middleware.py::test_unauthorized_role_blocked -x` | Wave 0 |
| VIEWAS-08 | Admin can view any active missionary | integration | `pytest apps/core/tests/test_middleware.py::test_admin_can_view_as_any_missionary -x` | Wave 0 |
| VIEWAS-08 | Supervisor blocked for non-assigned missionary | integration | `pytest apps/core/tests/test_middleware.py::test_supervisor_blocked_for_unassigned -x` | Wave 0 |
| VIEWAS-08 | Supervisor allowed for assigned missionary | integration | `pytest apps/core/tests/test_middleware.py::test_supervisor_allowed_for_assigned -x` | Wave 0 |
| VIEWAS-08 | Non-existent user ID → 403 | integration | `pytest apps/core/tests/test_middleware.py::test_invalid_user_id_returns_403 -x` | Wave 0 |
| VIEWAS-08 | Inactive target → 403 | integration | `pytest apps/core/tests/test_middleware.py::test_inactive_target_returns_403 -x` | Wave 0 |
| VIEWAS-08 | get_visible_user_ids returns target set when view_as_user set | unit | `pytest apps/core/tests/test_permissions.py::test_view_as_overrides_scoping -x` | Wave 0 |
| VIEWAS-12 | Admin GET /api/users/viewable returns all missionaries | integration | `pytest apps/users/tests/test_views_viewable.py::test_admin_sees_all_missionaries -x` | Wave 0 |
| VIEWAS-12 | Supervisor GET /api/users/viewable returns only assigned | integration | `pytest apps/users/tests/test_views_viewable.py::test_supervisor_sees_assigned_only -x` | Wave 0 |
| VIEWAS-12 | Missionary GET /api/users/viewable returns 403 | integration | `pytest apps/users/tests/test_views_viewable.py::test_missionary_gets_403 -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/core/tests/test_middleware.py apps/users/tests/test_views_viewable.py apps/core/tests/test_permissions.py -x`
- **Per wave merge:** `pytest --cov=apps --cov-fail-under=80`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/core/tests/test_middleware.py` — covers VIEWAS-07, VIEWAS-08 middleware behavior
- [ ] `apps/core/middleware.py` — ViewAsMiddleware implementation (Wave 0 creates stub/empty, Wave 1 implements)
- [ ] `apps/users/tests/test_views_viewable.py` — covers VIEWAS-12
- [ ] `apps/core/tests/test_permissions.py::test_view_as_overrides_scoping` — new test in existing file

Existing test file: `apps/core/tests/test_permissions.py` — already exists; new test appended, not a new file.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase read — `apps/core/permissions.py`, `apps/users/views.py`, `apps/users/urls.py`, `apps/users/models.py`, `apps/users/serializers.py`, `apps/users/views_assignments.py`, `config/settings/base.py`, `conftest.py`, `pyproject.toml`
- `52-CONTEXT.md` — locked decisions and architecture guidance

### Secondary (MEDIUM confidence)
- Django 4.2 middleware documentation pattern (`__init__`/`__call__` style) — well-established, consistent with project Django version
- DRF `Response({'detail': '...'}, status=403)` pattern — verified in multiple existing views

### Tertiary (LOW confidence)
- None — all findings verified directly from codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entire stack already present in codebase; no new dependencies
- Architecture: HIGH — patterns directly observed in existing code; decisions locked in CONTEXT.md
- Pitfalls: HIGH — pitfall 1 (JWT auth timing) verified against Django/DRF dispatch lifecycle; others verified from codebase patterns

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable Django/DRF codebase; no external dependencies changing)
