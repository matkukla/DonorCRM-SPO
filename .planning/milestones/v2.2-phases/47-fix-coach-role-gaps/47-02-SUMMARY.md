---
phase: 47-fix-coach-role-gaps
plan: "02"
subsystem: permissions
tags: [coach, permissions, rbac, tdd]
dependency_graph:
  requires: []
  provides: [coach-contact-read-access, role-03, role-04, role-05]
  affects: [apps/core/permissions.py, apps/contacts/tests/test_integration.py, apps/users/tests/test_views.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, safe-methods-guard]
key_files:
  created:
    - .planning/phases/47-fix-coach-role-gaps/deferred-items.md
  modified:
    - apps/core/permissions.py
    - apps/contacts/tests/test_integration.py
    - apps/users/tests/test_views.py
    - conftest.py
decisions:
  - "Coach added to SAFE_METHODS guard in IsStaffOrAbove (identical pattern to read_only) — not added to final allowed list to preserve write block"
  - "admin_user, missionary_user, coach_user fixtures added to root conftest.py for reuse across test suites"
metrics:
  duration: "4 min"
  completed: "2026-03-10"
  tasks_completed: 2
  files_modified: 4
requirements:
  - ROLE-03
  - ROLE-04
  - ROLE-05
---

# Phase 47 Plan 02: Fix IsStaffOrAbove Coach Permission Gate Summary

**One-liner:** One-line permission fix adds coach to SAFE_METHODS guard in IsStaffOrAbove, unlocking GET /api/v1/contacts/ (ROLE-03/05) while preserving 403 on writes — backed by 4 new regression tests.

## What Was Built

Added `'coach'` to the `read_only` safe-methods guard in `IsStaffOrAbove.has_permission`. Coach users were receiving 403 on all contact endpoints because `'coach'` was absent from `IsStaffOrAbove`. The data scoping in `get_visible_user_ids()` already handled coach correctly — only the permission gate was broken.

### Change Summary

**apps/core/permissions.py** (1 line changed):
- Line 86: `if request.user.role == 'read_only':` → `if request.user.role in ['read_only', 'coach']:`
- Coach is gated to SAFE_METHODS exactly like read_only
- Coach is NOT added to the final `return` allowed list — preserving write block

### Tests Added

**apps/contacts/tests/test_integration.py** — `TestCoachContactAccess` class:
- `test_coach_can_list_contacts` (ROLE-03): GET /api/v1/contacts/ returns 200
- `test_coach_cannot_create_contact` (ROLE-03 write block): POST returns 403
- `test_coach_contact_list_scoped_to_missionaries` (ROLE-05): GET returns 200 with scoped data

**apps/users/tests/test_views.py** — `TestCoachAssignment` class:
- `test_admin_can_set_coached_user_ids` (ROLE-04): Admin PATCH with coached_user_ids persists M2M

**conftest.py** — New fixtures:
- `admin_user`, `missionary_user`, `coach_user` fixtures for cross-suite reuse

## Verification Results

```
apps/contacts/tests/ + apps/users/tests/: 53 passed, 1 skipped
```

All success criteria met:
- IsStaffOrAbove gates coach to SAFE_METHODS (identical pattern to read_only)
- Coach users receive 200 on GET /api/v1/contacts/
- Coach users receive 403 on POST /api/v1/contacts/
- Admin PATCH with coached_user_ids persists M2M (test locked)
- `grep -n "coach" apps/core/permissions.py` shows coach in SAFE_METHODS guard only

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Out-of-Scope Pre-existing Failures

The following test failures exist in `apps/imports/tests/` and `apps/insights/tests/` and were confirmed pre-existing (present before any phase 47 changes via stash comparison). Logged to `deferred-items.md`:

- `TestGiftExport::test_export_gifts_csv`
- `TestActivityHeatmap` (4 tests)
- `TestTeamTrendsView::test_counts_donations_by_week`

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 484c7b1 | test | Add failing tests for ROLE-03, ROLE-04, ROLE-05 (RED) |
| a2b16d1 | fix | Allow coach safe-method access in IsStaffOrAbove (GREEN) |

## Self-Check: PASSED

- apps/core/permissions.py: FOUND
- apps/contacts/tests/test_integration.py: FOUND
- apps/users/tests/test_views.py: FOUND
- Commit 484c7b1 (RED tests): FOUND
- Commit a2b16d1 (permission fix): FOUND
