---
phase: 49-goal-page-data-model-backend
plan: 04
subsystem: api
tags: [django, drf, rest-api, goal-tracking, fiscal-year]

# Dependency graph
requires:
  - phase: 49-02
    provides: fiscal_year_start, months_remaining in apps.core.fiscal_year; _monthly_equivalent_aggregate in apps.core.gift_utils
  - phase: 49-03
    provides: User.monthly_support_goal_cents, User.goal_weeks, GoalJournalSelection model

provides:
  - apps/users/goal_services.py with get_goal_progress(user) returning 6-key dict
  - GET /api/v1/goals/me/ endpoint returning effective_monthly_support and goal config
  - PATCH /api/v1/goals/me/ endpoint for updating goal amount, weeks, and journal selections
  - URL registered at path('goals/', include('apps.users.urls_goals'))

affects: [goal-frontend-50, phase-50]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GoalView follows existing CurrentUserView APIView pattern: permission_classes=[IsAuthenticated], GET/PATCH methods, no serializer class"
    - "Replace-all journal selection: GoalJournalSelection.objects.filter(user=user).delete() then bulk_create for atomic replacement"
    - "Owner scoping in service layer: JournalContact filtered by journal__owner=user before aggregating gifts"

key-files:
  created:
    - apps/users/goal_services.py
    - apps/users/views_goals.py
    - apps/users/urls_goals.py
  modified:
    - config/api_urls.py
    - apps/users/tests/test_views_goals.py

key-decisions:
  - "GoalView does not use a serializer class — reads request.data directly and returns get_goal_progress() dict, following existing CurrentUserView pattern"
  - "selected_journal_ids returned as list of strings (str(jid)) for consistent JSON serialization — UUID objects serialize to strings in JSON"

patterns-established:
  - "Goal service layer: compute-only function returns plain dict, no model save side effects"
  - "Journal selection replace-all: delete-then-bulk_create within same request handler"

requirements-completed: [GOAL-02, GOAL-03, GOAL-04, GOAL-11]

# Metrics
duration: 15min
completed: 2026-03-13
---

# Phase 49 Plan 04: Goal Service and API Endpoint Summary

**Django REST API for GET/PATCH /api/v1/goals/me/ backed by get_goal_progress() service computing recurring + one-time fiscal-year gift totals from journal-scoped contacts**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-13T03:26:31Z
- **Completed:** 2026-03-13T03:41:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- goal_services.py: get_goal_progress(user) returns all 6 dict keys including effective_monthly_support = recurring_monthly + one_time_monthly
- GoalView APIView: GET returns progress dict, PATCH updates goal cents/weeks and replaces journal selections atomically
- URL registered at /api/v1/goals/me/ via new urls_goals.py and config/api_urls.py entry
- All 4 test_goal_services.py tests and all 5 test_views_goals.py tests pass GREEN
- New files have 100% code coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement get_goal_progress() in goal_services.py** - `694cc22` (feat)
2. **Task 2: Implement GoalView and register URL at /api/v1/goals/me/** - `165ae9d` (feat)

**Plan metadata:** *(final commit hash — recorded after docs commit)*

## Files Created/Modified
- `apps/users/goal_services.py` - get_goal_progress(user) service: contacts scoped via journal__owner=user, _monthly_equivalent_aggregate for recurring, Sum(amount_cents) for one-time gifts
- `apps/users/views_goals.py` - GoalView APIView with GET/PATCH; replace-all journal selection via delete+bulk_create
- `apps/users/urls_goals.py` - URL pattern path('me/', GoalView.as_view(), name='goal-me')
- `config/api_urls.py` - Added path('goals/', include('apps.users.urls_goals'))
- `apps/users/tests/test_views_goals.py` - Fixed UUID type comparison bug in 2 assertions

## Decisions Made
- GoalView does not use a DRF serializer — reads request.data directly and returns get_goal_progress() dict, following existing CurrentUserView pattern for simplicity
- selected_journal_ids returned as list of strings (str(jid)) for consistent JSON serialization across all UUID fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UUID type comparison in test_views_goals.py assertions**
- **Found during:** Task 2 (GREEN verification run)
- **Issue:** Two assertions compared `set(data["selected_journal_ids"])` (list of UUID strings from JSON) against `{j1.id, j2.id}` (UUID objects). Python `str != UUID` so assertion always fails.
- **Fix:** Updated both assertions to `{str(j1.id), str(j2.id)}` and `[str(j1.id)]` respectively
- **Files modified:** apps/users/tests/test_views_goals.py
- **Verification:** All 5 test_views_goals.py tests pass GREEN
- **Committed in:** 165ae9d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix necessary to make tests pass — stub was written with incorrect type assumption. No scope creep.

## Issues Encountered
- Pre-existing coverage at 68% (below 80% threshold) due to unrelated failures in apps/imports and apps/insights — these are out-of-scope for Plan 04. New files have 100% coverage.

## Next Phase Readiness
- Phase 50 (Goal frontend) is unblocked: GET /api/v1/goals/me/ and PATCH /api/v1/goals/me/ are fully functional
- Response contract: {monthly_support_goal_cents, goal_weeks, selected_journal_ids, effective_monthly_support, recurring_monthly, one_time_monthly}
- Phase 49 is complete — all 4 plans finished

---
*Phase: 49-goal-page-data-model-backend*
*Completed: 2026-03-13*
