---
phase: 46-multiple-supervisors-per-missionary
plan: "05"
subsystem: frontend-admin
tags: [admin, users, m2m, supervisor, coach, typescript]
dependency_graph:
  requires: [46-04]
  provides: [AdminUsers-M2M-fix]
  affects: [frontend/src/pages/admin/AdminUsers.tsx]
tech_stack:
  added: []
  patterns: [M2M array-includes pattern replacing scalar FK filter]
key_files:
  created: []
  modified:
    - frontend/src/pages/admin/AdminUsers.tsx
decisions:
  - "Frontend derivation for supervised/coached IDs: filter all users by role='missionary' and u.supervisor_ids.includes(supervisorUser.id) — avoids backend change"
  - "Read-only missionary list added as separate labeled section above the editable picker — improves UX clarity for supervisor/coach edit dialogs"
metrics:
  duration: "5min"
  completed: "2026-03-08"
  tasks: 1
  files: 1
---

# Phase 46 Plan 05: Fix AdminUsers.tsx Scalar FK Assumptions Summary

**One-liner:** Replaced scalar `u.supervisor/u.coach` FK filter patterns in AdminUsers.tsx with M2M `u.supervisor_ids?.includes()/u.coach_ids?.includes()` array patterns, and added labeled read-only missionary lists to supervisor/coach edit dialogs.

## What Was Done

Fixed `AdminUsers.tsx` which had two broken patterns referencing removed scalar FK fields (`supervisor` and `coach`) on the `User` interface after Plan 46-04 updated the API to M2M arrays.

### Task 1: Fix AdminUsers.tsx scalar FK assumptions and add missionary list display

**Commit:** d58fbae

**Changes made:**

1. **`openEditDialog()` fix (lines ~137-141):** Replaced:
   ```typescript
   const supervised = users?.filter(u => u.supervisor === user.id).map(u => u.id) || []
   const coached = users?.filter(u => u.coach === user.id).map(u => u.id) || []
   ```
   With M2M array-includes derivation:
   ```typescript
   const supervised = users?.filter(u =>
     u.role === 'missionary' && u.supervisor_ids?.includes(user.id)
   ).map(u => u.id) ?? []
   const coached = users?.filter(u =>
     u.role === 'missionary' && u.coach_ids?.includes(user.id)
   ).map(u => u.id) ?? []
   ```

2. **Count display in table rows:** Replaced `u.supervisor === user.id` and `u.coach === user.id` in the table row badge counts with the same array-includes pattern, filtered to role='missionary'.

3. **Read-only missionary list in edit dialog:** Added a labeled "Currently Assigned Missionaries" section as read-only Badge chips (no X button) above the editable multi-select picker for both supervisor and coach role users. Shows "No missionaries currently assigned" when list is empty.

## Verification

- `npx tsc --noEmit`: Zero errors
- `npx vite build`: Build succeeded (dist/ created)
- Backend pytest: Pre-existing failures unrelated to this frontend-only change (is_staff_role attribute missing, staff role invalid in test fixtures — these pre-date phase 46)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `frontend/src/pages/admin/AdminUsers.tsx` modified
- [x] Commit d58fbae exists
- [x] Zero TypeScript errors
- [x] `openEditDialog()` uses array-includes pattern
- [x] Count display uses array-includes pattern
- [x] Supervisor/coach edit dialog shows labeled read-only missionary list

## Self-Check: PASSED
