---
phase: 46-multiple-supervisors-per-missionary
plan: "04"
subsystem: frontend
tags: [typescript, react, admin-ui, assignments, multi-select]
dependency_graph:
  requires: [46-03]
  provides: [frontend-m2m-assignment-ui]
  affects: [frontend/src/api/users.ts, frontend/src/pages/admin/AdminAssignments.tsx]
tech_stack:
  added: []
  patterns: [Popover+Command multi-select, Badge chips with X remove, view mode toggle]
key_files:
  created: []
  modified:
    - frontend/src/api/users.ts
    - frontend/src/pages/admin/AdminAssignments.tsx
decisions:
  - "SupervisorCell and CoachCell extracted as sub-components to keep the main component readable"
  - "bulkDirty Set tracks rows modified via bulk apply (send additive=true); individually edited rows use additive=false"
  - "Supervisor view is read-only — editing done only in missionary view"
metrics:
  duration: "2 minutes"
  completed_date: "2026-03-07"
  tasks: 2
  files: 2
---

# Phase 46 Plan 04: Frontend M2M Assignment UI Summary

**One-liner:** Rewrote AdminAssignments.tsx with Popover+Command multi-select chip UI for M2M supervisor/coach assignments, plus missionary/supervisor view toggle with additive bulk apply.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Update api/users.ts TypeScript interfaces | eaff8e7 | frontend/src/api/users.ts |
| 2 | Rewrite AdminAssignments.tsx with multi-select chips and view toggle | 277509d | frontend/src/pages/admin/AdminAssignments.tsx |

## What Was Built

**Task 1 — TypeScript interface updates (api/users.ts):**
- `MissionaryAssignment`: removed `supervisor_id`/`coach_id` scalars, added `supervisor_ids: string[]` / `coach_ids: string[]`
- `AssignmentUpdate`: removed scalars, added arrays + `additive?: boolean`
- `User`: removed `supervisor`/`coach` scalar FK fields, added `supervisor_ids`/`coach_ids` arrays

**Task 2 — AdminAssignments.tsx rewrite:**
- Local state map now uses `{ supervisor_ids: string[]; coach_ids: string[] }` per missionary
- Two Popover+Command multi-select cells (Supervisor, Coach columns) with checkmark toggle
- Badge chips below each trigger with X button for individual removal
- Missionary/Supervisor view mode toggle: missionary view for editing, supervisor view (read-only) showing missionaries grouped under each supervisor
- Bulk bar uses additive mode: selects a single supervisor/coach to add across selected missionaries
- `bulkDirty` Set tracks which rows were bulk-applied to send `additive: true` on save
- Soft warning toast fires when a missionary reaches 5+ supervisors
- Grid columns changed to `grid-cols-[40px_1fr_1fr_1fr_32px]` for flexible chip cells

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Cleanup] Removed unused missionaryId and missionaryName props from sub-components**
- **Found during:** Task 2 implementation
- **Issue:** SupervisorCellProps and CoachCellProps initially had missionaryId props that weren't used inside the sub-components (callbacks captured closure values instead)
- **Fix:** Removed the unused props from the interface definitions and call sites; TypeScript confirmed no errors
- **Files modified:** frontend/src/pages/admin/AdminAssignments.tsx

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| SupervisorCell + CoachCell as sub-components | Keeps per-row popover open state local, main component stays readable |
| bulkDirty Set for additive tracking | Clean separation: bulk adds = additive=true, individual edits = full replace (additive=false) |
| Supervisor view is read-only | Editing from supervisor perspective is complex; missionary view is the primary editing surface |
| ChevronsUpDown icon on bulk bar dropdowns | Consistent with AdminUsers.tsx Popover trigger pattern |

## Self-Check: PASSED

- frontend/src/api/users.ts — modified with supervisor_ids/coach_ids arrays: CONFIRMED
- frontend/src/pages/admin/AdminAssignments.tsx — rewritten with multi-select: CONFIRMED
- Commit eaff8e7 (Task 1): CONFIRMED
- Commit 277509d (Task 2): CONFIRMED
- TypeScript: no errors in AdminAssignments.tsx or api/users.ts: CONFIRMED
