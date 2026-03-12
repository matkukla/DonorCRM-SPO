---
status: complete
phase: 48-mpd-dashboard-enhancements
source: [48-01-SUMMARY.md, 48-02-SUMMARY.md]
started: 2026-03-12T16:40:00Z
updated: 2026-03-12T17:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Monthly Average tile on MPD Dashboard (missionary view)
expected: On the Dashboard, the MPD Financial Overview section shows 4 cards in a responsive grid (2 columns on small screens, 4 columns on medium+). The first card is "Monthly Average" and displays the user's monthly average MPD value (or a dash/null if not set).
result: pass

### 2. Monthly Average in /api/v1/imports/mpd/me/ response
expected: Calling GET /api/v1/imports/mpd/me/ (as a missionary) returns a JSON response that includes a "monthly_average" key. The value is either a numeric string (e.g. "1500.00") or null if not set.
result: skipped
reason: Data visible in UI confirms API works; browser fetch blocked by auth cookie issue in DevTools

### 3. Monthly Average in /api/v1/imports/mpd/overview/ response
expected: Calling GET /api/v1/imports/mpd/overview/ (as an admin) returns a JSON array of missionaries. Each entry includes a "monthly_average" key positioned before "current_mpd_cap". Value is a numeric string or null.
result: skipped
reason: Covered by automated TDD tests in plan 48-01; admin overview table (test 4) will verify data end-to-end

### 4. Admin MPD Overview table on Dashboard
expected: When logged in as an admin on your own dashboard (not viewing as another user), a "MPD Overview" table section appears below the MPD cards. It shows all missionaries with columns: Missionary | Monthly Average | MPD Cap | Roll Forward Balance | Months Remaining. The Monthly Average column is sortable.
result: pass

### 5. Admin MPD Overview table hidden when using View As
expected: When an admin uses "View As" to browse a missionary's dashboard, the MPD Overview table does NOT appear — it is hidden entirely. Only the missionary's own MPD cards are shown.
result: pass

### 6. MPD Overview table not shown to missionaries
expected: When logged in as a missionary (non-admin), the MPD Overview table section does not appear anywhere on the Dashboard — only the 4 MPD cards are visible.
result: pass

## Summary

total: 6
passed: 4
issues: 0
pending: 0
skipped: 2

## Gaps

[none yet]
