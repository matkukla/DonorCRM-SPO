---
phase: 52-view-as-backend
verified: 2026-03-16T00:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 52: View As Backend Verification Report

**Phase Goal:** The backend can validate View As permissions, return the correct list of viewable users per role, and block all mutating requests when the X-View-As-User-Id header is present.
**Verified:** 2026-03-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                             | Status     | Evidence                                                                                       |
|----|---------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| 1  | POST/PUT/PATCH/DELETE with X-View-As-User-Id header returns 403 Forbidden                        | VERIFIED   | All 4 mutation tests pass; middleware returns "Mutations are not allowed in View As mode."   |
| 2  | GET with X-View-As-User-Id header passes through (not blocked)                                   | VERIFIED   | test_get_allowed_in_view_as PASSED; test_admin_can_view_as_any_missionary PASSED             |
| 3  | Missionary sending header gets 403                                                                | VERIFIED   | test_unauthorized_role_blocked PASSED; error: "You do not have permission to view as this user." |
| 4  | Admin sending header for valid missionary target has request.view_as_user set                    | VERIFIED   | middleware.py line 116: `request.view_as_user = target`; GET passes through                 |
| 5  | Supervisor sending header for non-assigned missionary gets 403                                    | VERIFIED   | test_supervisor_blocked_for_unassigned PASSED                                                |
| 6  | Non-existent or inactive target UUID returns 403                                                 | VERIFIED   | test_invalid_user_id_returns_403 PASSED; test_inactive_target_returns_403 PASSED            |
| 7  | get_visible_user_ids() returns {view_as_user.id} when request.view_as_user is set               | VERIFIED   | test_view_as_overrides_scoping PASSED; permissions.py lines 41-44 implement branch          |
| 8  | GET /api/v1/users/viewable/ returns correct list per role; 403 for missionary; shape is {id, full_name} | VERIFIED | All 7 test_views_viewable.py tests pass                                                     |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact                            | Expected                                              | Status     | Details                                                                                        |
|-------------------------------------|-------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| `apps/core/middleware.py`           | ViewAsMiddleware class                                | VERIFIED   | Exists, 118 lines, substantive — _resolve_viewer, _validate_and_attach, _json_403 all present |
| `config/settings/base.py`           | ViewAsMiddleware in MIDDLEWARE list                   | VERIFIED   | Line 64: `'apps.core.middleware.ViewAsMiddleware'` after AuthenticationMiddleware             |
| `apps/core/permissions.py`          | get_visible_user_ids(user, request=None) with view_as override | VERIFIED | Line 20: signature confirmed; lines 41-44: view_as branch as first branch               |
| `apps/users/views.py`               | ViewableUsersView class                               | VERIFIED   | Lines 112-142: full admin/supervisor branching with role='missionary', is_active=True filter  |
| `apps/users/serializers.py`         | ViewableUserSerializer class                          | VERIFIED   | Lines 219-226: id (UUIDField) + full_name (CharField) only                                   |
| `apps/users/urls.py`                | viewable/ path registered before uuid:pk             | VERIFIED   | Line 22: `path('viewable/', ...)` appears before `path('<uuid:pk>/', ...)`                   |
| `apps/core/tests/test_middleware.py` | 12 passing tests for VIEWAS-07 and VIEWAS-08          | VERIFIED   | All 12 PASSED                                                                                 |
| `apps/users/tests/test_views_viewable.py` | 7 passing tests for VIEWAS-12                   | VERIFIED   | All 7 PASSED                                                                                 |
| `apps/core/tests/test_permissions.py` | test_view_as_overrides_scoping appended and passing | VERIFIED   | Line 108-119: test present and PASSED (7 total tests pass)                                   |

### Key Link Verification

| From                                     | To                                  | Via                                                      | Status  | Details                                                                        |
|------------------------------------------|-------------------------------------|----------------------------------------------------------|---------|--------------------------------------------------------------------------------|
| `config/settings/base.py MIDDLEWARE`     | `apps.core.middleware.ViewAsMiddleware` | Django MIDDLEWARE list after AuthenticationMiddleware | WIRED   | Line 64, position after AuthenticationMiddleware (line 63) confirmed           |
| `ViewAsMiddleware.__call__`              | `request.view_as_user`              | `_validate_and_attach` sets attribute on request         | WIRED   | middleware.py line 116: `request.view_as_user = target`                       |
| `apps/core/permissions.get_visible_user_ids` | `request.view_as_user`          | `getattr(request, 'view_as_user', None)` first branch    | WIRED   | permissions.py lines 41-44 confirmed                                           |
| All 14 view/export files                 | `get_visible_user_ids`              | `get_visible_user_ids(user, request=self.request)`       | WIRED   | grep confirms zero bare `get_visible_user_ids(user)` calls without request in any view/export file |
| `apps/users/urls.py viewable/ path`      | `apps/users/views.ViewableUsersView` | `path('viewable/', ViewableUsersView.as_view(), ...)`   | WIRED   | urls.py line 22; ViewableUsersView imported line 11                            |
| `ViewableUsersView.get`                  | `User.objects.filter(role='missionary', is_active=True)` | admin branch queryset         | WIRED   | views.py lines 126-130 confirmed                                               |

**Note on dashboard/services.py:** Three bare `get_visible_user_ids(user)` calls remain in dashboard/services.py at lines 49, 147, and 201. This is intentional by design (documented in 52-03-SUMMARY.md): those functions receive the target user directly from `_resolve_target_user(request)` in the view layer and do not participate in View As data scoping. Not a gap.

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                | Status     | Evidence                                                    |
|-------------|-------------|--------------------------------------------------------------------------------------------|------------|-------------------------------------------------------------|
| VIEWAS-07   | 52-01, 52-02 | Backend enforces read-only: mutations return 403 when X-View-As-User-Id header is present | SATISFIED  | 4 mutation tests pass; middleware.py lines 45-46            |
| VIEWAS-08   | 52-01, 52-02, 52-03 | Backend validates viewer has permission before allowing View As                      | SATISFIED  | Permission tests pass; data scoping via request param threaded to all 14 view files |
| VIEWAS-12   | 52-01, 52-04 | GET /api/users/viewable returns correct list of users per role                             | SATISFIED  | 7 endpoint tests pass; ViewableUsersView + URL registered   |

All three required requirement IDs (VIEWAS-07, VIEWAS-08, VIEWAS-12) are accounted for. No orphaned requirements for Phase 52 found in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO/FIXME/placeholder/stub returns detected in any implementation file.

### Human Verification Required

None. All behaviors are verifiable programmatically:
- Mutation blocking is exercised by integration tests against real Django test client.
- Permission validation is exercised by tests with role-specific factory users.
- Data scoping override is verified by unit test with mock request.
- Endpoint shape is verified by `test_response_shape` asserting `set(item.keys()) == {'id', 'full_name'}`.

### Test Run Summary

```
26 passed, 46 warnings in 2.05s
```

Files covered:
- `apps/core/tests/test_middleware.py`: 12/12 PASSED
- `apps/users/tests/test_views_viewable.py`: 7/7 PASSED
- `apps/core/tests/test_permissions.py`: 7/7 PASSED (6 pre-existing + 1 new)

### Gaps Summary

No gaps. All must-haves are satisfied. The phase goal is fully achieved:
- Mutations are blocked at the middleware layer for any request carrying the X-View-As-User-Id header.
- Permission validation (admin vs supervisor vs other roles, target validity, supervisor assignment check) is enforced before the mutation guard.
- request.view_as_user is set on every valid authenticated GET, and get_visible_user_ids() reads it as the first branch — all 14 view/export files pass request through.
- GET /api/v1/users/viewable/ returns the correct scoped list for admin and supervisor, 403 for all other roles, with a two-field response shape (id + full_name only).

---

_Verified: 2026-03-16_
_Verifier: Claude (gsd-verifier)_
