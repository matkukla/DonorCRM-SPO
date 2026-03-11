---
phase: 43-roles-redesign
plan: 02
subsystem: api
tags: [django, permissions, rbac, coach, assignments]

# Dependency graph
requires:
  - phase: 43-01
    provides: New role model with coach/supervisor/missionary roles, coached_users relation, is_financial_role helper

provides:
  - Coach blocked from financial data (gifts views return none(), export returns 403)
  - Coach blocked from financial insights endpoints (donations by month/year, monthly commitments, late donations)
  - Coach allowed to use owner filter param in contacts views
  - mission_supervisor string replaced with supervisor across all non-test view files
  - New AssignmentsView API at /api/v1/users/admin/assignments/ (GET + PATCH)

affects: [43-03, 43-04, 43-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Coach financial exclusion: check user.role == 'coach' at top of get_queryset() to return none()"
    - "is_financial_role() guard: check before returning financial aggregate data in insights views"
    - "AssignmentsView pattern: admin-only endpoint using IsAdmin permission + PATCH with per-item error collection"

key-files:
  created:
    - apps/users/views_assignments.py
  modified:
    - apps/gifts/views.py
    - apps/gifts/export_views.py
    - apps/insights/views.py
    - apps/insights/services.py
    - apps/contacts/views.py
    - apps/contacts/export_views.py
    - apps/users/urls.py

key-decisions:
  - "Coach financial block uses get_queryset() none() pattern (not 403) for gifts list/detail — matches plan spec"
  - "CSV export uses HttpResponseForbidden for coach (not 404) — explicit rejection for financial export"
  - "is_financial_role() check in insights views uses early return (not permission_classes) — per plan spec"
  - "get_user_performance() updated from role__in=['staff','admin'] to ['missionary','admin'] to match renamed roles"
  - "Owner filter expanded to include coach alongside admin and supervisor in contacts/export views"

patterns-established:
  - "Financial data guard: role check before returning any donation/pledge aggregate data"
  - "AssignmentsView: GET returns typed lists (missionaries/supervisors/coaches), PATCH accepts list with per-item error collection"

requirements-completed: []

# Metrics
duration: 12min
completed: 2026-03-04
---

# Phase 43 Plan 02: Backend Views + API Summary

**Coach financial exclusion across gifts/insights views, mission_supervisor->supervisor string sweep, and new AssignmentsView API at /api/v1/users/admin/assignments/**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-04T22:15:00Z
- **Completed:** 2026-03-04T22:27:00Z
- **Tasks:** 6
- **Files modified:** 7 + 1 created

## Accomplishments
- Coach role blocked from financial data: gifts list/detail return empty querysets, CSV exports return 403
- Financial insights endpoints (donations by month/year, monthly commitments, late donations) now reject coach via is_financial_role()
- Owner filter expanded to include coach in contacts views/export_views (so coach can filter by coached user)
- All `mission_supervisor` strings replaced with `supervisor` in non-test view files
- `get_user_performance()` updated from `['staff', 'admin']` to `['missionary', 'admin']` in insights services
- New AssignmentsView with GET (returns missionaries/supervisors/coaches) and PATCH (bulk update assignments)
- Assignments URL wired at `admin/assignments/` in users URL config

## Task Commits

Each task was committed atomically:

1. **Task 1: Block coach from financial data in gifts views** - `ecac3db` (feat)
2. **Task 2: Block coach from insights/financial views** - `1c94e7c` (feat)
3. **Task 3: Expand owner filter for coach in contacts** - `8af0c2a` (feat)
4. **Task 4: String sweep across all view files** - `6adea0a` (chore)
5. **Task 5: Create Assignments API endpoint** - `5d836b1` (feat)
6. **Task 6: Wire assignments URL** - `73e3b25` (feat)

## Files Created/Modified
- `apps/gifts/views.py` - Added coach check to all 4 get_queryset() methods returning none()
- `apps/gifts/export_views.py` - Added HttpResponseForbidden for coach in both export views; replaced mission_supervisor with supervisor
- `apps/insights/views.py` - Imported is_financial_role; added checks in 4 financial data views
- `apps/insights/services.py` - Replaced role__in=['staff','admin'] with ['missionary','admin'] in get_user_performance()
- `apps/contacts/views.py` - Expanded owner filter from ['admin','mission_supervisor'] to ['admin','supervisor','coach']
- `apps/contacts/export_views.py` - Expanded owner filter from ['admin','mission_supervisor'] to ['admin','supervisor','coach']
- `apps/users/views_assignments.py` - New AssignmentsView with GET and PATCH methods (IsAdmin protected)
- `apps/users/urls.py` - Added admin/assignments/ URL pattern

## Decisions Made
- Coach financial block in gifts uses `return Gift.objects.none()` (empty queryset) rather than 403 — per plan spec, coach sees empty list
- CSV exports use `HttpResponseForbidden` (not empty CSV) for coach — explicit rejection is correct for file downloads
- is_financial_role() added as inline check in insights views (not as permission_classes) — preserves IsAuthenticated class while adding role check
- Owner filter expanded to include coach so coached users can be filtered in contacts/export views

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all tasks executed cleanly, `python manage.py check` passes with 0 issues.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Coach financial exclusion complete on backend — frontend can safely hide financial tabs for coach
- AssignmentsView ready for frontend Assignments page (Plan 43-04)
- String rename complete across all non-test view files — tests with old role strings will need updating in a future plan
