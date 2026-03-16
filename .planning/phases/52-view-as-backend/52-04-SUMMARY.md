---
phase: 52-view-as-backend
plan: "04"
subsystem: api
tags: [django, rest-framework, view-as, permissions, serializer]

# Dependency graph
requires:
  - phase: 52-view-as-backend
    provides: test scaffold with 7 failing tests for /api/v1/users/viewable/ (52-01)
provides:
  - GET /api/v1/users/viewable/ endpoint returning [{id, full_name}] list of missionaries
  - ViewableUserSerializer (id + full_name only, no sensitive fields)
  - ViewableUsersView with admin/supervisor role branching + 403 for other roles
affects:
  - 53-view-as-frontend (will call this endpoint to populate View As dropdown)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - APIView subclass with role-based queryset branching (admin vs supervisor vs 403)
    - Minimal serializer exposing only two fields for sensitive data reduction

key-files:
  created: []
  modified:
    - apps/users/serializers.py
    - apps/users/views.py
    - apps/users/urls.py
    - apps/users/tests/test_views_viewable.py

key-decisions:
  - "viewable/ URL registered before <uuid:pk>/ in urlpatterns to prevent literal path being caught by UUID converter"
  - "Supervisor branch uses supervised_users.filter(role='missionary', is_active=True) — M2M can theoretically hold any role, so double-filter is required"
  - "Test URL corrected from /api/users/viewable/ to /api/v1/users/viewable/ to match actual URL prefix"

patterns-established:
  - "ViewableUserSerializer pattern: two-field ModelSerializer (id+full_name) for secure public exposure of user data"

requirements-completed:
  - VIEWAS-12

# Metrics
duration: 15min
completed: 2026-03-16
---

# Phase 52 Plan 04: Viewable Users Endpoint Summary

**GET /api/v1/users/viewable/ endpoint returning [{id, full_name}] for admin (all active missionaries) and supervisor (assigned missionaries only), with 403 for missionary role**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-16T15:10:00Z
- **Completed:** 2026-03-16T15:22:21Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- ViewableUserSerializer appended to serializers.py with only id (UUIDField) and full_name (CharField) — no email, role, or other sensitive data
- ViewableUsersView added to views.py with admin/supervisor role branching and is_active + role='missionary' double-filter on supervisor branch
- viewable/ URL registered before <uuid:pk>/ pattern to prevent routing collision
- All 7 tests in test_views_viewable.py pass, full users test suite passes with 53 tests (1 skipped migration test, pre-existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ViewableUserSerializer** - `0c9dd1e` (feat)
2. **Task 2: Add ViewableUsersView and register URL** - `99c515a` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tests were scaffolded in Plan 01 (RED state). Plan 04 brought them to GREEN._

## Files Created/Modified
- `apps/users/serializers.py` - Appended ViewableUserSerializer class
- `apps/users/views.py` - Added ViewableUserSerializer import + ViewableUsersView class
- `apps/users/urls.py` - Added ViewableUsersView import + viewable/ path before <uuid:pk>/
- `apps/users/tests/test_views_viewable.py` - Fixed URL prefix from /api/users/ to /api/v1/users/ (auto-fix)

## Decisions Made
- URL ordering: `viewable/` registered before `<uuid:pk>/` — Django URL routing is first-match and `viewable` would fail UUID parsing
- Supervisor branch uses `supervised_users.filter(role='missionary', is_active=True)` not just `supervised_users.all()` — M2M can hold any role, double-filter is the safe path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect URL prefix in test file**
- **Found during:** Task 2 (running tests for the first time after implementation)
- **Issue:** test_views_viewable.py used `/api/users/viewable/` but the actual URL pattern is `/api/v1/users/viewable/` (all API endpoints are prefixed with `/api/v1/`)
- **Fix:** Replaced all 7 occurrences of `/api/users/viewable/` with `/api/v1/users/viewable/` in the test file
- **Files modified:** `apps/users/tests/test_views_viewable.py`
- **Verification:** All 7 tests pass after fix
- **Committed in:** `99c515a` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Auto-fix necessary for test correctness. The test scaffold from Plan 01 used the wrong URL prefix. No scope creep.

## Issues Encountered
- test_views_viewable.py had `/api/users/viewable/` instead of `/api/v1/users/viewable/` — all tests returned 404 until fixed. Root cause: Plan 01 test scaffold did not verify the URL against the actual API prefix convention used throughout the project.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GET /api/v1/users/viewable/ endpoint complete and tested
- VIEWAS-12 satisfied
- Phase 53 (View As frontend) can now call this endpoint to populate the View As dropdown selector
- No blockers

## Self-Check: PASSED

All artifacts verified:
- `apps/users/serializers.py` — FOUND
- `apps/users/views.py` — FOUND
- `apps/users/urls.py` — FOUND
- `.planning/phases/52-view-as-backend/52-04-SUMMARY.md` — FOUND
- Commit `0c9dd1e` — FOUND
- Commit `99c515a` — FOUND

---
*Phase: 52-view-as-backend*
*Completed: 2026-03-16*
