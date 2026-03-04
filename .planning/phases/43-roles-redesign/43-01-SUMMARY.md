---
phase: 43
plan: 1
subsystem: users/permissions
tags: [roles, migration, permissions, backend]
dependency_graph:
  requires: [42-01]
  provides: [new-role-names, coach-fk, permissions-update]
  affects: [all-backend-views-using-role-checks]
tech_stack:
  added: []
  patterns: [self-referencing-fk, run-python-data-migration]
key_files:
  created:
    - apps/users/migrations/0005_roles_redesign.py
  modified:
    - apps/users/models.py
    - apps/core/permissions.py
    - apps/users/serializers.py
    - apps/users/views.py
    - apps/users/tests/factories.py
decisions:
  - "Atomic migration: data migration (RunPython) BEFORE AlterField to avoid constraint violations on existing role values"
  - "coach excluded from IsStaffOrAbove (cannot write financial data) — added is_financial_role() helper to express this explicitly"
  - "supervised_users field name kept in CurrentUserSerializer — frontend consumes it for both supervisor and coach roles"
metrics:
  duration: ~3min
  completed: 2026-03-04
---

# Phase 43 Plan 1: DB Migrations + Backend Model Foundation Summary

**One-liner:** Atomic migration renames staff->missionary and mission_supervisor->supervisor, adds coach FK, and updates all backend model/permission code to the new role names.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Migration 0005_roles_redesign.py | fe7acab | apps/users/migrations/0005_roles_redesign.py |
| 2 | Update apps/users/models.py | c4d73b7 | apps/users/models.py |
| 3 | Update apps/core/permissions.py | cf402f5 | apps/core/permissions.py |
| 4 | Update apps/users/serializers.py | 8c3eb9f | apps/users/serializers.py |
| 5 | Update apps/users/views.py | 2d59f72 | apps/users/views.py |
| 6 | Update test factories + final check | e5d6dcc | apps/users/tests/factories.py |

## Key Changes

### Migration (0005_roles_redesign.py)
- `RunPython` data migration renames `staff`->`missionary` and `mission_supervisor`->`supervisor` in existing DB rows FIRST
- `AlterField` updates role choices/default to `'missionary'` with new choices: `missionary, admin, finance, read_only, supervisor, coach`
- `AddField` adds `coach` FK (self-referencing, SET_NULL, `related_name='coached_users'`, column `coach_id`)

### Model (models.py)
- `UserRole` enum: `STAFF`->`MISSIONARY`, `MISSION_SUPERVISOR`->`SUPERVISOR`, add `COACH`
- Default role updated to `UserRole.MISSIONARY`
- `coach` FK field added (mirrors migration)
- Properties: `is_staff_role`->`is_missionary`, `is_mission_supervisor`->`is_supervisor`, add `is_coach`
- `can_view_contact()` updated with coach branch (same logic as supervisor using `coached_users`)

### Permissions (permissions.py)
- `get_visible_user_ids()`: `'mission_supervisor'`->`'supervisor'`, add `'coach'` branch for `coached_users`
- `IsStaffOrAbove.has_permission()`: `'staff'`->`'missionary'`, `'mission_supervisor'`->`'supervisor'`, exclude `'coach'`
- New `is_financial_role()` helper: returns True for all roles except coach
- Docstring updated to reflect new role matrix

### Serializers (serializers.py)
- `UserSerializer`: add `coach_id` to fields
- `CurrentUserSerializer.get_supervised_users()`: handles both `'supervisor'` and `'coach'` roles (returns coached_users for coach)

### Views (views.py)
- `UserListCreateView` and `UserDetailView`: add `'coached_users'` to `prefetch_related()`

### Factories (factories.py)
- `UserFactory.role`: `UserRole.STAFF` -> `UserRole.MISSIONARY`

## Verification

- `python manage.py check` — no issues (0 silenced)
- `python manage.py showmigrations users` — 0005_roles_redesign shows `[X]`
- UserRole choices confirmed: `['missionary', 'admin', 'finance', 'read_only', 'supervisor', 'coach']`

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- apps/users/migrations/0005_roles_redesign.py: FOUND
- apps/users/models.py: FOUND
- apps/core/permissions.py: FOUND
- apps/users/serializers.py: FOUND
- apps/users/views.py: FOUND
- apps/users/tests/factories.py: FOUND
- Commits fe7acab, c4d73b7, cf402f5, 8c3eb9f, 2d59f72, e5d6dcc: all verified
