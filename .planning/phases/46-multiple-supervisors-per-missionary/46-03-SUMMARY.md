---
phase: 46-multiple-supervisors-per-missionary
plan: "03"
subsystem: users
tags: [m2m, serializers, api, supervisor, coach]
dependency_graph:
  requires: [46-02]
  provides: [46-04, 46-05]
  affects: [apps/users/serializers.py, apps/users/models.py, apps/users/views_assignments.py]
tech_stack:
  added: []
  patterns:
    - SerializerMethodField for M2M arrays
    - User.save() override for auto-clearing M2M on role change
key_files:
  created: []
  modified:
    - apps/users/serializers.py
    - apps/users/models.py
    - apps/users/views_assignments.py
decisions:
  - Auto-clear on role change implemented in User.save() (not serializer) because the test calls sup.save() directly
  - warnings list added to AssignmentsView PATCH response for soft limit >= 5 supervisors
metrics:
  duration: "~3min"
  completed: "2026-03-07"
  tasks_completed: 2
  files_modified: 3
---

# Phase 46 Plan 03: Backend API M2M Layer Summary

**One-liner:** M2M supervisor/coach arrays fully exposed via UserSerializer and AssignmentsView with role-change auto-clear in User.save().

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update serializers.py — M2M field exposure and auto-unassign | 4a6ede7 | apps/users/serializers.py, apps/users/models.py |
| 2 | Add warnings list to AssignmentsView PATCH response | c524eef | apps/users/views_assignments.py |

## What Was Built

### Task 1: UserSerializer M2M Exposure + Auto-Unassign on Role Change

**UserSerializer** now exposes `supervisor_ids` and `coach_ids` as `SerializerMethodField` returning string arrays. The stale scalar `supervisor` and `coach_id` FK fields are removed from `Meta.fields`.

**Auto-unassign on role change:** Added `User.save()` override that detects when a user's role changes away from `supervisor` or `coach` and clears the corresponding M2M relation (`supervised_users.clear()` / `coached_users.clear()`). This was placed in the model rather than the serializer because the integration test calls `sup.save()` directly (not via serializer), and the model is the correct layer for invariant enforcement.

**UserAdminUpdateSerializer.update()** was already converted to M2M `.set()` by the Wave 2 executor — no changes needed there.

### Task 2: AssignmentsView PATCH Warnings List

The Wave 2 executor had already fully implemented the GET (prefetch_related, arrays) and PATCH (additive flag, .set()/.add()). This task added the missing `warnings` list to the response, emitting a soft warning when a missionary ends up with 5+ supervisors after a PATCH operation.

## Test Results

All 6 runnable tests in `test_m2m_assignments.py` pass GREEN:
- `TestM2MModelBehaviors` (2 tests): missionary multi-supervisor, get_visible_user_ids for both supervisors
- `TestAssignmentsViewM2M` (3 tests): GET returns arrays, PATCH additive, PATCH replace
- `TestAutoUnassignOnRoleChange` (1 test): supervised_users cleared when supervisor becomes missionary
- 1 test skipped (migration test, requires `--migrations` flag)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Auto-clear in User.save() not serializer**

- **Found during:** Task 1
- **Issue:** The plan specified auto-clear logic in `UserAdminUpdateSerializer.update()`, but the integration test calls `sup.save()` directly. The serializer path would never trigger during that test.
- **Fix:** Added `User.save()` override to capture the old role via a lightweight DB query before saving, then clear M2M after save if role changed away from supervisor/coach.
- **Files modified:** apps/users/models.py
- **Commit:** 4a6ede7

### Pre-existing Failures (Out of Scope)

The following test failures existed before this plan and are unrelated to M2M changes:
- `apps/contacts/tests/test_integration.py::TestDonorWorkflow::test_complete_donor_journey` (403 on contact create)
- `apps/users/tests/test_models.py::TestUserModel::test_role_properties` (missing `is_staff_role` attribute)
- `apps/users/tests/test_views.py::TestUserListView::test_admin_can_create_user` (invalid role 'staff')
- `apps/insights/tests/test_date_filtering.py::TestActivityHeatmap` (multiple tests)

These are logged to deferred items.

## Self-Check: PASSED

- apps/users/serializers.py: FOUND
- apps/users/models.py: FOUND
- apps/users/views_assignments.py: FOUND
- Commit 4a6ede7: FOUND
- Commit c524eef: FOUND
