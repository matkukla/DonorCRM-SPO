---
phase: quick-14
plan: 14
subsystem: frontend-assignments
tags: [assignments, supervisor-view, editable, react]
dependency_graph:
  requires: []
  provides: [editable-supervisor-view]
  affects: [AdminAssignments]
tech_stack:
  added: []
  patterns: [MissionaryCell sub-component, toggleMissionaryForSupervisor handler]
key_files:
  created: []
  modified:
    - frontend/src/pages/admin/AdminAssignments.tsx
decisions:
  - MissionaryCell mirrors SupervisorCell/CoachCell pattern — per-row popover state, badge list with X buttons
  - supervisorId prop omitted from MissionaryCell interface; supervisor ID closed over in onToggle/onRemove at call site
  - Sticky save bar condition widened from viewMode===missionary to unconditional dirty.size>0 — both views share the same dirty Set
metrics:
  duration: "< 5 min"
  completed: "2026-03-10"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 14: Make By Supervisor View Editable — Summary

**One-liner:** Editable supervisor view with MissionaryCell popover + badge sub-component using the existing dirty-tracking and save infrastructure.

## What Was Built

The "By Supervisor" tab in `/admin/assignments` was read-only (static badges). This task made it fully editable by:

1. Adding `toggleMissionaryForSupervisor(missionaryId, supervisorId)` handler that mutates `localAssignments` and marks the missionary dirty — same pattern as `toggleSupervisor` and `toggleCoach`.

2. Replacing the read-only badge block in the supervisor view rows with a new `MissionaryCell` sub-component that renders:
   - A popover combobox ("Assign missionary...") with search and checkmarks
   - Removable badge chips for each currently-assigned missionary

3. Extending the sticky save bar from missionary-view-only to both views (condition changed from `viewMode === "missionary" && dirty.size > 0` to `dirty.size > 0`).

4. Adding the `MissionaryCell` function component at the bottom of the file, alongside `SupervisorCell` and `CoachCell`.

## Verification

- `npx tsc --noEmit` — no errors
- By Supervisor view: each supervisor row shows "Assign missionary..." popover button
- Selecting a missionary adds badge and shows sticky save bar
- Clicking X on a badge removes the missionary
- Saving via the sticky bar persists changes through existing `updateMutation` infrastructure

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `frontend/src/pages/admin/AdminAssignments.tsx` modified (confirmed)
- [x] Commit `4342fc2` exists (confirmed)
- [x] TypeScript compiles clean (confirmed)

## Self-Check: PASSED
