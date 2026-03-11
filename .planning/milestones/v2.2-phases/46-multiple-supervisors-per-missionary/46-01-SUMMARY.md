---
phase: 46-multiple-supervisors-per-missionary
plan: "01"
subsystem: users/tests
tags: [tdd, red-tests, m2m, supervisors, nyquist-gate]
dependency_graph:
  requires: []
  provides: [behavioral-contracts-for-m2m-supervisors]
  affects: [apps/users/tests/test_m2m_assignments.py, apps/users/tests/factories.py]
tech_stack:
  added: []
  patterns: [pytest-django, factory_boy, RED-before-GREEN TDD]
key_files:
  created:
    - apps/users/tests/test_m2m_assignments.py
  modified:
    - apps/users/tests/factories.py
decisions:
  - "SupervisorUserFactory and CoachUserFactory inherit from UserFactory; unique email sequences via factory.Sequence to avoid DB collisions"
  - "Migration test (Test 7) marked skip with comment directing to --migrations flag; avoids false RED vs. collection error ambiguity"
  - "Test for supervised_users.count() after role change uses reverse M2M manager — contracts Plan 02 to name it supervised_users"
metrics:
  duration_seconds: 196
  tasks_completed: 2
  files_modified: 2
  completed_date: "2026-03-07"
---

# Phase 46 Plan 01: RED Tests for M2M Supervisor/Coach Behaviors — Summary

**One-liner:** Failing RED test suite establishing M2M behavioral contracts for supervisors/coaches — AttributeError on `user.supervisors` confirms model not yet migrated.

## What Was Built

Added two new user factories and created a complete RED test file covering all M2M supervisor/coach behaviors. All 6 active tests fail with `AttributeError: 'User' object has no attribute 'supervisors'`, confirming the model changes in Plan 02 are required before any test passes.

### Task 1: SupervisorUserFactory and CoachUserFactory (factories.py)

Added two subclass factories at the bottom of `apps/users/tests/factories.py`:
- `SupervisorUserFactory` — role=SUPERVISOR, unique email sequence (`supervisor{n}@example.com`)
- `CoachUserFactory` — role=COACH, unique email sequence (`coach{n}@example.com`)

Both follow the established pattern of subclassing `UserFactory` with role and email overrides.

### Task 2: test_m2m_assignments.py (RED tests)

Created `apps/users/tests/test_m2m_assignments.py` with 3 test classes and 7 test functions:

| Class | Tests | Behavioral Contract |
|-------|-------|---------------------|
| `TestM2MModelBehaviors` | 2 | Multi-supervisor assignment + get_visible_user_ids independence |
| `TestAssignmentsViewM2M` | 3 | GET returns `supervisor_ids` list; PATCH additive vs. replace |
| `TestAutoUnassignOnRoleChange` | 1 | Role change clears supervised_users M2M |
| `test_migration_preserves_...` | 1 (skipped) | FK→M2M data migration preservation |

**RED state confirmed:** `6 failed, 1 skipped` — no collection errors.

## Deviations from Plan

None — plan executed exactly as written. The migration test is skipped (not xfail) with a clear comment per plan instructions.

## Verification Results

```
SKIPPED [1] Migration test: run pytest --migrations to verify
FAILED TestM2MModelBehaviors::test_missionary_can_have_multiple_supervisors
FAILED TestM2MModelBehaviors::test_get_visible_user_ids_returns_missionary_for_both_supervisors
FAILED TestAssignmentsViewM2M::test_get_returns_supervisor_ids_as_list
FAILED TestAssignmentsViewM2M::test_patch_additive_appends_supervisor_assignments
FAILED TestAssignmentsViewM2M::test_patch_non_additive_replaces_supervisor_assignments
FAILED TestAutoUnassignOnRoleChange::test_supervised_users_cleared_when_supervisor_becomes_missionary
6 failed, 1 skipped, 24 warnings in 0.74s
```

All failures: `AttributeError: 'User' object has no attribute 'supervisors'`

## Self-Check: PASSED

- [x] `apps/users/tests/test_m2m_assignments.py` — 267 lines, 7 test functions, 3 classes
- [x] `apps/users/tests/factories.py` — SupervisorUserFactory and CoachUserFactory present
- [x] Commit `a449387` — factories
- [x] Commit `55389d4` — RED test file
- [x] All tests collected without import errors
- [x] All 6 active tests fail in RED state (not collection errors)
