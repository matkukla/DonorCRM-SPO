---
status: complete
phase: 46-multiple-supervisors-per-missionary
source: [46-01-SUMMARY.md, 46-02-SUMMARY.md, 46-03-SUMMARY.md, 46-04-SUMMARY.md, 46-05-SUMMARY.md]
started: 2026-03-08T05:00:00Z
updated: 2026-03-08T05:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Assign Multiple Supervisors to a Missionary
expected: Go to Admin > Assignments. In missionary view, find a missionary row. Click the Supervisor cell — a multi-select popover opens showing available supervisors. Select two or more supervisors (checkmarks appear). Close the popover. Badge chips for each selected supervisor appear in the cell. Click Save — the assignment persists and reloads correctly showing all selected supervisors.
result: pass

### 2. Remove a Supervisor via Badge Chip X
expected: In missionary view, a missionary with 2+ supervisors shows badge chips. Click the X on one chip — that supervisor is removed from the list immediately (locally). Click Save — the missionary now has one fewer supervisor and it persists on reload.
result: pass

### 3. Assign Multiple Coaches to a Missionary
expected: In the Coach cell, click to open the multi-select popover. Select multiple coaches. Chips appear. Save — multiple coaches are assigned and display correctly on reload.
result: pass

### 4. Supervisor View Mode (Read-Only)
expected: Toggle to "Supervisor view" mode. The grid shows supervisors listed, each with their assigned missionaries displayed beneath (read-only). There is no edit capability in this view — all assignment editing is done in missionary view.
result: pass

### 5. Bulk Apply Supervisor Across Multiple Missionaries
expected: In missionary view, check multiple missionary rows. The bulk action bar appears. Select a supervisor from the bulk supervisor dropdown. Click Apply — that supervisor is ADDED (additive) to all selected missionaries without replacing their existing supervisors. Save — all selected missionaries now include the bulk-added supervisor.
result: pass

### 6. Soft Warning at 5+ Supervisors
expected: Assign a 5th (or more) supervisor to a missionary. A toast warning appears indicating the missionary has a high number of supervisors. The assignment still saves successfully — it's a soft warning, not a block.
result: pass

### 7. Auto-Unassign on Role Change
expected: In Admin > Users, find a user with role=Supervisor who has missionaries assigned. Change their role to Missionary (or any non-supervisor role). Save. Navigate to Admin > Assignments — that user no longer appears as a supervisor for any missionaries. The M2M assignment was automatically cleared when the role changed.
result: pass

### 8. Supervisor Count Display in AdminUsers Table
expected: Go to Admin > Users. For a user with role=Supervisor, their row shows the correct count of missionaries they supervise. This count updates correctly based on M2M assignments (not stale scalar FK data).
result: pass

### 9. Supervisor Edit Dialog Shows Current Missionaries
expected: In Admin > Users, click Edit on a supervisor user. The edit dialog shows a labeled "Currently Assigned Missionaries" section with read-only badge chips for each missionary currently assigned to them. If none are assigned, it shows "No missionaries currently assigned".
result: issue
reported: "I've noticed a discrepancy between Users and Assignments. For example, Wendy Burger isn't a user but is shown in Assignments as a supervisor"
severity: major

### 10. Missionary supervisor_ids in API Response
expected: Open browser devtools or test via the API — a GET request to the users/assignments endpoint for a missionary returns supervisor_ids as an array (e.g., ["uuid1", "uuid2"]), not a scalar field. Similarly coach_ids is an array. No stale supervisor or coach_id scalar fields appear.
result: pass

## Summary

total: 10
passed: 9
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Supervisor Edit Dialog shows only users that exist in the Users list (Admin > Users)"
  status: failed
  reason: "User reported: Wendy Burger isn't a user but is shown in Assignments as a supervisor"
  severity: major
  test: 9
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
