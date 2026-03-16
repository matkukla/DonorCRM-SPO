---
status: resolved
phase: 51-data-scoping-admin-supervisor-default-to-own-data
source: 51-01-SUMMARY.md, 51-02-SUMMARY.md, 51-03-SUMMARY.md
started: 2026-03-16T13:30:00Z
updated: 2026-03-16T17:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Permission Tests All Pass
expected: Run: pytest apps/core/tests/test_permissions.py -v — all 6 tests pass (GREEN). Admin, supervisor, finance, read_only, coach, missionary all return correct result sets.
result: pass

### 2. Admin Sees Only Own Data in the App
expected: Log in as an admin user. Navigate to any data list (Contacts, Donations, Tasks, etc.). The admin should only see records assigned to themselves — not records belonging to other users. Previously, admins saw everyone's data by default.
result: pass

### 3. Supervisor Sees Only Own Data (Not Supervised Missionaries' Data)
expected: Log in as a supervisor user. Navigate to any data list (Contacts, Donations, Tasks, etc.). The supervisor should see only their own records — not their supervised missionaries' records. Previously, supervisors saw both their own and their missionaries' data.
result: pass

### 4. Finance Sees All Data (All-Access Unchanged)
expected: Log in as a finance user. Navigate to any data list. Finance should still see ALL records across all users — this role was not changed and must remain all-access.
result: pass

### 5. Read-Only Sees All Data (All-Access Unchanged)
expected: Log in as a read_only user. Navigate to any data list. Read-only should still see ALL records across all users — this role was not changed and must remain all-access.
result: issue
reported: "There shouldn't be a read_only role. A supervisor or admin should be able to see all the contacts, pledges, donations, etc. of a missionary once it is selected in the dropdown on the dashboard"
severity: major

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "read_only role should not exist; admin/supervisor should see a selected missionary's full data (contacts, pledges, donations) via a dashboard dropdown selector"
  status: resolved
  reason: "User reported: There shouldn't be a role as read_only. A supervisor or admin should be able to see all the contacts, pledges, donations, etc. of a missionary once it is selected in the dropdown on the dashboard"
  severity: major
  test: 5
  resolution: |
    Three sub-issues — all addressed:
    A) read_only role removal — tracked in separate phase (future roadmap item).
    B) Dashboard selector cross-page View As context — addressed by Phase 52 (View As backend) and Phase 53 (View As frontend).
    C) PHASE 51 REGRESSION fixed by plan 51-03: _resolve_target_user() now has a role guard that short-circuits for admin/supervisor, allowing them to select any active user via ?user_id= param without hitting the get_visible_user_ids() check. 4 regression tests added and passing.
  root_cause: |
    Three distinct issues bundled:
    A) read_only role exists throughout the system (22 backend files, 6 frontend files) — removal is a product decision requiring its own phase with DB migration.
    B) Dashboard missionary selector is dashboard-local only; contacts/pledges/donations/etc do not change when missionary selected — this is Phase 52/53 scope (View As backend + frontend context).
    C) PHASE 51 REGRESSION: _resolve_target_user() in apps/dashboard/views.py now blocks supervisors from viewing their assigned missionaries via the dashboard ?user_id= param. Phase 51 changed get_visible_user_ids() to return {user.id} for supervisors, so the permission check raises 403 PermissionDenied when a supervisor selects a missionary from the dropdown. This worked before Phase 51.
  artifacts:
    - path: "apps/dashboard/views.py"
      issue: "FIXED in 51-03 — _resolve_target_user() now has role guard before get_visible_user_ids() check"
    - path: "apps/core/permissions.py"
      issue: "get_visible_user_ids() correctly returns {user.id} for supervisor; dashboard selector uses separate guard"
    - path: "apps/users/models.py"
      issue: "UserRole.READ_ONLY — tracked for future phase removal"
    - path: "frontend/src/pages/Dashboard.tsx"
      issue: "Missionary selector cross-page context — Phase 52/53 scope"
  missing:
    - "Phase 52: View As backend middleware + GET /api/users/viewable/ endpoint"
    - "Phase 53: ViewAsContext in frontend, X-View-As-User-Id header injection across all API calls"
    - "Separate phase for read_only role removal with DB migration and full audit"
