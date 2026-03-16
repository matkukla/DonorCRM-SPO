---
phase: 52-view-as-backend
plan: 02
subsystem: api
tags: [django, middleware, jwt, drf, view-as, permissions, mutation-blocking]

# Dependency graph
requires:
  - phase: 52-view-as-backend
    provides: "RED test scaffold for ViewAsMiddleware (12 tests in test_middleware.py)"
provides:
  - "ViewAsMiddleware class in apps/core/middleware.py — validates X-View-As-User-Id header, blocks mutations, attaches target to request.view_as_user"
  - "MIDDLEWARE list updated in config/settings/base.py with apps.core.middleware.ViewAsMiddleware"
affects: [52-03-permissions-update, 52-04-viewable-endpoint, 53-view-as-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Viewer resolution tri-path: _force_auth_user (test hook) > session auth > JWT Bearer parse — allows middleware to authenticate before DRF dispatch"
    - "Mutation guard runs AFTER _validate_and_attach — permission check precedes mutation check so invalid targets get correct error (not mutation error)"
    - "DRF Response with explicit renderer for 403s — allows response.data['detail'] access from both DRF test client and plain HTTP clients"

key-files:
  created:
    - apps/core/middleware.py
  modified:
    - config/settings/base.py
    - apps/core/tests/test_middleware.py

key-decisions:
  - "_resolve_viewer() checks request._force_auth_user first (DRF test hook) so force_authenticate() works correctly in tests where Django's AuthenticationMiddleware only sets AnonymousUser for JWT-only sessions"
  - "Returns DRF Response (not django.http.JsonResponse) with accepted_renderer=JSONRenderer so response.data['detail'] is accessible — required by test assertions"
  - "Test URLs fixed from /api/ to /api/v1/ — test scaffold (Plan 01) used wrong prefix; fixed as Rule 1 (Bug) during this plan"
  - "JWT Bearer path in _resolve_viewer handles production requests where neither _force_auth_user nor session auth sets request.user"

patterns-established:
  - "Viewer resolution before view dispatch: middleware reads _force_auth_user/session/JWT to resolve viewer independently of DRF dispatch"
  - "DRF Response in Django middleware: set accepted_renderer, accepted_media_type, renderer_context, call render() for HTTP response compatibility"

requirements-completed: [VIEWAS-07, VIEWAS-08]

# Metrics
duration: 18min
completed: 2026-03-16
---

# Phase 52 Plan 02: ViewAsMiddleware Implementation Summary

**ViewAsMiddleware blocking POST/PUT/PATCH/DELETE with 403 and validating admin/supervisor-only header access, registered in Django MIDDLEWARE after AuthenticationMiddleware**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-16T15:12:29Z
- **Completed:** 2026-03-16T15:31:13Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- ViewAsMiddleware implemented with full permission validation: role guard (admin/supervisor only), target validation (missionary, active, exists), supervisor-assignment check
- Mutation blocking returns 403 for POST/PUT/PATCH/DELETE with the header when viewer is valid — GET passes through with request.view_as_user set
- Unauthenticated requests pass through (DRF returns 401 naturally)
- All 12 tests in test_middleware.py pass GREEN, zero regressions in existing 20 core tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement ViewAsMiddleware and register in settings** - `41ca13d` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `apps/core/middleware.py` — ViewAsMiddleware class with _resolve_viewer, _validate_and_attach, _json_403 helpers
- `config/settings/base.py` — Added apps.core.middleware.ViewAsMiddleware after AuthenticationMiddleware
- `apps/core/tests/test_middleware.py` — Fixed test URLs from /api/ to /api/v1/ (bug fix)

## Decisions Made
- `_resolve_viewer()` checks `_force_auth_user` first: DRF's `force_authenticate()` sets this attribute on the raw Django request before middleware runs, but Django's `AuthenticationMiddleware` only sees session cookies, so JWT-authenticated test requests appeared anonymous at middleware time. Checking `_force_auth_user` enables tests to work correctly.
- Used `rest_framework.response.Response` instead of `django.http.JsonResponse` for 403 responses: the DRF test client exposes `.data` only on DRF Response objects, and the test assertions use `response.data['detail']`. Response rendered immediately with `JSONRenderer` so it's compatible with Django's response pipeline.
- Mutation guard placed after `_validate_and_attach`: an admin with a valid target who sends POST gets "Mutations are not allowed", while an admin with an invalid target gets "Invalid View As target." regardless of HTTP method.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test URLs from /api/ to /api/v1/**
- **Found during:** Task 1 (first test run, all tests returning 404)
- **Issue:** Test scaffold (Plan 01) used `/api/contacts/` but the actual URL prefix is `/api/v1/contacts/` per config/urls.py
- **Fix:** Updated all 9 URL references in test_middleware.py from `/api/` to `/api/v1/`
- **Files modified:** apps/core/tests/test_middleware.py
- **Verification:** test_unauthenticated_with_header immediately passed after fix (401 instead of 404)
- **Committed in:** 41ca13d (Task 1 commit)

**2. [Rule 1 - Bug] Added _resolve_viewer() for JWT/force_authenticate compatibility**
- **Found during:** Task 1 (tests returning 201/405/200 instead of 403 after URL fix)
- **Issue:** Middleware checked `request.user.is_authenticated` which is always False at middleware time for DRF JWT-authenticated requests (DRF auth runs in APIView.dispatch(), after middleware)
- **Fix:** Added `_resolve_viewer()` that checks three sources: `request._force_auth_user` (test hook), session auth, and JWT Bearer token parsing via JWTAuthentication
- **Files modified:** apps/core/middleware.py
- **Verification:** 8 previously-failing tests now pass GREEN
- **Committed in:** 41ca13d (Task 1 commit)

**3. [Rule 1 - Bug] Used DRF Response instead of JsonResponse for 403s**
- **Found during:** Task 1 (403 status correct but `response.data['detail']` AttributeError)
- **Issue:** `django.http.JsonResponse` has no `.data` attribute; DRF test client expects `rest_framework.response.Response`
- **Fix:** Replaced `JsonResponse` with `Response` using `_json_403()` helper that sets renderer and renders immediately
- **Files modified:** apps/core/middleware.py
- **Verification:** All 12 tests pass, `response.data['detail']` works correctly
- **Committed in:** 41ca13d (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (3x Rule 1 - Bug)
**Impact on plan:** All three fixes necessary to make the tests pass. URL fix corrects test scaffold error. Viewer resolution and Response type fixes handle DRF middleware integration issues not anticipated in plan spec. No scope creep.

## Issues Encountered
- Coverage plugin raises PermissionError on htmlcov directory — pre-existing issue, worked around with `--no-cov` flag (documented in Plan 01 summary as well)

## Next Phase Readiness
- ViewAsMiddleware live — request.view_as_user populated on all authenticated GET requests with valid header
- Plan 03 (permissions update) can now update get_visible_user_ids() to accept request kwarg and read request.view_as_user for scoping override
- Plan 04 (viewable endpoint) can implement ViewableUsersView that returns supervised missionaries list

---
*Phase: 52-view-as-backend*
*Completed: 2026-03-16*
