# Phase 52: View As — Backend - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend infrastructure for View As mode: a Django middleware that validates the X-View-As-User-Id header, blocks all mutating requests when View As is active, attaches the target user to the request, and updates get_visible_user_ids() to scope data to the target. Also adds GET /api/users/viewable/ returning the list of missionaries the viewer can impersonate. No frontend changes in this phase.

</domain>

<decisions>
## Implementation Decisions

### Middleware placement
- Django middleware in `apps/core/middleware.py` (not a DRF permission class)
- Sits in the MIDDLEWARE stack; attaches validated target User object to `request.view_as_user`
- Blocks mutations (POST, PUT, PATCH, DELETE) globally before DRF even sees the request
- Zero per-view changes needed — all views benefit automatically

### get_visible_user_ids() update
- Updated in Phase 52 (not deferred to Phase 53)
- Signature change: accepts optional `request` parameter so it can read `request.view_as_user`
- When `request.view_as_user` is set: returns `{view_as_user.id}` regardless of viewer role
- All callers (contacts, gifts, journals, tasks, prayers, groups, events, dashboard, insights) pick up data scoping automatically through the existing call sites

### Who can use the header
- Admin and supervisor roles only — any other role sending the header gets a 403
- Target user must be role='missionary' and is_active=True
- Admin: can view any active missionary
- Supervisor: can only view missionaries in their `supervised_users` M2M relation

### Invalid/unauthorized header handling
- Non-existent user ID → 403 Forbidden
- Target user not in viewer's permitted set → 403 Forbidden
- Viewer role is not admin or supervisor → 403 Forbidden
- All cases use HTTP 403 (not 400) — treats bad header values as a permission violation

### Error response shape
- Simple `{"detail": "..."}` string format — matches DRF default 403 format used throughout the codebase
- Distinct messages per failure case:
  - Mutation blocked: `"Mutations are not allowed in View As mode."`
  - Unauthorized viewer or target not in permitted set: `"You do not have permission to view as this user."`
  - Target user not found or inactive: `"Invalid View As target."`

### GET /api/users/viewable endpoint
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

</decisions>

<specifics>
## Specific Ideas

- The middleware approach keeps this surgical: no per-view changes, all 40+ views get mutation blocking and data scoping for free through existing call sites
- `get_visible_user_ids()` is the single choke point from Phase 51 — updating it here means every list view, export, and dashboard tile automatically scopes to the target missionary when View As is active

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/core/permissions.py` → `get_visible_user_ids(user)`: Already the single choke point for all list view scoping. Needs signature update to accept request/view_as_user.
- `apps/users/views.py` → existing `UserListCreateView`, `CurrentUserView`: Pattern for new `ViewableUsersView` to follow.
- `apps/users/urls.py`: Already has `/me/`, `/admin/assignments/` — `/viewable/` fits the same pattern.
- `apps/users/models.py` → `supervised_users` M2M field: Used in the supervisor permission check.

### Established Patterns
- `visible is None` sentinel: All callers check `if visible is None: queryset = all()`. After Phase 51, admin/supervisor never return None. After Phase 52, view_as_user check returns `{view_as_user.id}` — all existing callers work without modification.
- DRF permission classes (`IsAdmin`, `IsSupervisorWriteRestricted`): New `ViewableUsersView` uses `IsAdmin | IsSupervisor` style permission to restrict the endpoint.
- `{"detail": "..."}` error format: `Response({"detail": "..."}, status=403)` matches how all existing permission failures are returned.

### Integration Points
- `config/settings/base.py` MIDDLEWARE list: New `ViewAsMiddleware` added after `AuthenticationMiddleware`
- `apps/core/permissions.py` → `get_visible_user_ids()`: Signature and body update
- `apps/users/urls.py`: New `viewable/` path
- `apps/users/views.py`: New `ViewableUsersView` class
- All callers of `get_visible_user_ids()` need the `request` passed through — check: contacts/views.py, gifts/views.py, journals/views.py, tasks/views.py, prayers/views.py, groups/views.py, events/views.py, dashboard/views.py, dashboard/services.py (user-scoped functions only)

</code_context>

<deferred>
## Deferred Ideas

- Coach View As support (view their coached missionaries) — deferred to v2.4+ per VIEWAS-EX-01
- Audit log of View As sessions (who viewed whom and when) — deferred to v2.4+ per VIEWAS-EX-02

</deferred>

---

*Phase: 52-view-as-backend*
*Context gathered: 2026-03-16*
