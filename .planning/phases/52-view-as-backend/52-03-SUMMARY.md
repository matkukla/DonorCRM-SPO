---
phase: 52-view-as-backend
plan: "03"
subsystem: permissions
tags: [view-as, data-scoping, permissions, middleware]
dependency_graph:
  requires: [52-01]
  provides: [VIEWAS-08-data-scoping]
  affects: [contacts, journals, gifts, tasks, prayers, events, groups, insights, dashboard]
tech_stack:
  added: []
  patterns:
    - "request=None optional parameter on get_visible_user_ids() for backward compatibility"
    - "view_as override as first branch — checked before role logic"
    - "_scope_* helper pattern in insights/services.py forwarding request param"
key_files:
  created: []
  modified:
    - apps/core/permissions.py
    - apps/contacts/views.py
    - apps/contacts/export_views.py
    - apps/prayers/views.py
    - apps/dashboard/views.py
    - apps/events/views.py
    - apps/insights/services.py
    - apps/insights/views.py
    - apps/journals/views.py
    - apps/journals/export_views.py
    - apps/groups/views.py
    - apps/gifts/views.py
    - apps/gifts/export_views.py
    - apps/tasks/views.py
    - apps/tasks/export_views.py
decisions:
  - "[52-03]: dashboard/services.py not updated — target user already resolved via _resolve_target_user(request) in view layer, no request threading needed"
  - "[52-03]: prayers/_owner_scoped_queryset() gains request=None param and all 3 callers updated — needed because the helper is called from method and function-based views"
  - "[52-03]: insights service functions (_scope_gifts/_scope_recurring_gifts/_scope_tasks + callers) gain request=None — view-context-only functions, safe to update signatures"
  - "[52-03]: JournalAnalyticsViewSet._get_visible uses request=self.request — consistent with other class-based views in the viewset"
metrics:
  duration: "17 minutes"
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_modified: 15
---

# Phase 52 Plan 03: Data Scoping via get_visible_user_ids() Summary

Updated `get_visible_user_ids()` to accept an optional `request` parameter and check for `request.view_as_user`, then threaded `request` through all 14 caller files so View As mode automatically scopes every list view to the target missionary's data.

## Tasks Completed

| # | Task | Commit | Type |
|---|------|--------|------|
| 1 | Update get_visible_user_ids() signature + view_as override branch | fc1c101 | TDD GREEN |
| 2 | Update all call sites to pass request through | 2558050 | feat |

## What Was Built

### Task 1: Updated get_visible_user_ids()

`apps/core/permissions.py` — changed signature from `get_visible_user_ids(user)` to `get_visible_user_ids(user, request=None)` and added a view_as override as the first branch:

```python
if request is not None:
    view_as_user = getattr(request, 'view_as_user', None)
    if view_as_user is not None:
        return {view_as_user.id}
```

All 6 existing tests still pass. New `test_view_as_overrides_scoping` turned GREEN.

### Task 2: All Call Sites Updated

Every view-level and export-view-level call site now passes `request=self.request` (class-based views) or `request=request` (function-based views):

- `apps/contacts/views.py` — 11 call sites
- `apps/contacts/export_views.py` — 1 call site
- `apps/prayers/views.py` — `_owner_scoped_queryset()` helper updated + 3 callers
- `apps/dashboard/views.py` — 2 call sites (`_resolve_target_user` + `UserDashboardLayoutView`)
- `apps/events/views.py` — 2 call sites
- `apps/insights/services.py` — 3 `_scope_*` helpers + 4 service function signatures
- `apps/insights/views.py` — 4 service call sites updated
- `apps/journals/views.py` — 9 call sites + `_get_visible()` method
- `apps/journals/export_views.py` — 1 call site
- `apps/groups/views.py` — 4 call sites
- `apps/gifts/views.py` — 4 call sites
- `apps/gifts/export_views.py` — 2 call sites
- `apps/tasks/views.py` — 5 call sites
- `apps/tasks/export_views.py` — 1 call site

`apps/dashboard/services.py` intentionally NOT updated — those functions receive the target user directly from `_resolve_target_user(request)` in the view layer.

## Verification

All bare call sites removed from view/export files:
```
grep -rn "get_visible_user_ids(user)" apps/ --include="*.py" \
  | grep -v "def get_visible_user_ids" | grep -v "test_" | grep -v "dashboard/services.py"
# Returns: 0 results
```

All 19 tests pass:
- 7 tests in `test_permissions.py` (6 existing + 1 new `test_view_as_overrides_scoping`)
- 12 tests in `test_middleware.py`

## Deviations from Plan

### Auto-additions (not strictly bugs, but required completeness)

**1. [Rule 2 - Missing functionality] prayers/views.py — _owner_scoped_queryset helper**
- **Found during:** Task 2
- **Issue:** Plan said "1 call site" in prayers/views.py but `_owner_scoped_queryset()` is a standalone helper called from 3 places (PrayerIntentionListCreateView, PrayerIntentionDetailView, MarkPrayedView, TodaysFocusView). Updating only the direct call sites without updating the helper would leave scoping broken for Detail and Mark Prayed views.
- **Fix:** Added `request=None` param to `_owner_scoped_queryset()` and updated all 4 callers to pass `request=self.request` or `request=request`.
- **Files modified:** `apps/prayers/views.py`
- **Commit:** 2558050

**2. [Rule 2 - Missing functionality] insights/services.py — service function signatures**
- **Found during:** Task 2
- **Issue:** Plan's "simpler alternative" for insights required updating `_scope_*` helpers AND propagating `request` through the higher-level service functions (`get_donations_by_month`, `get_donations_by_year`, `get_monthly_commitments`, `get_follow_ups`) that call them, otherwise views couldn't pass request down the call chain.
- **Fix:** Added `request=None` to all 4 service functions and updated insights/views.py call sites.
- **Files modified:** `apps/insights/services.py`, `apps/insights/views.py`
- **Commit:** 2558050 (insights/views.py was noted as expected in plan)

## Self-Check: PASSED

- SUMMARY.md: FOUND at `.planning/phases/52-view-as-backend/52-03-SUMMARY.md`
- Commit fc1c101: FOUND (Task 1 — permissions.py)
- Commit 2558050: FOUND (Task 2 — all call sites)
