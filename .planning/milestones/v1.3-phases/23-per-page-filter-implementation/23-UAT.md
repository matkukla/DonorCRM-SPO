---
status: complete
phase: 23-per-page-filter-implementation
source: 23-01-SUMMARY.md, 23-02-SUMMARY.md, 23-03-SUMMARY.md
started: 2026-02-18T18:00:00Z
updated: 2026-02-18T18:05:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Donation FilterBar with Amount Range
expected: |
  Navigate to Donations page. You should see a FilterBar above the data table with: search input, Type dropdown, Payment dropdown, Status dropdown, two date inputs, two amount inputs (Min $ / Max $), a Fund dropdown, and (if admin) an Owner dropdown. Enter a min amount (e.g. 100) — the table should filter to show only donations >= $100. Enter a max amount (e.g. 500) — table shows only $100-$500 donations. Amount inputs appear in URL as ?amount_min=100&amount_max=500.
awaiting: complete

number: 11
name: URL Persistence Across Pages
expected: |
  On Donations page, apply a few filters (e.g. type=One-time, amount_min=50). Copy the URL. Open a new tab and paste the URL. The page loads with the same filters applied and the same filtered results displayed.
awaiting: complete

## Tests

### 1. Donation FilterBar with Amount Range
expected: Navigate to Donations page. FilterBar shows search, Type, Payment, Status dropdowns, date range, amount range (Min $ / Max $), Fund dropdown, and Owner dropdown (admin only). Enter min amount 100 and max 500 — table filters to donations in that range. URL shows ?amount_min=100&amount_max=500.
result: pass (re-test after fix fe42102)

### 2. Donation Fund Filter
expected: On Donations page, click the "All Funds" dropdown in the FilterBar. You should see a list of your active funds. Select one — the table filters to only donations associated with that fund. A filter badge appears showing the fund name.
result: pass

### 3. Donation Admin Owner Filter
expected: (Admin only — skip if not admin) On Donations page, you should see an "All Owners" dropdown. Click it to see a list of missionaries. Select one — table shows only that missionary's donations. Badge shows the owner name.
result: pass

### 4. Donation Presets and CSV Export
expected: On Donations page, click a preset button (e.g. "This Month" or "Needs Thank You"). Filters auto-apply and badges update. Click the Export CSV button — a CSV file downloads containing only the currently filtered donations (not all donations).
result: pass

### 5. Donation Filter Badges and Clear All
expected: On Donations page, apply several filters (type, date range, amount). Filter badges appear below the filter controls showing each active filter. Click the X on one badge — that filter clears. Click "Clear All" — all filters reset and table shows all donations.
result: pass

### 6. Pledge Search by Donor Name
expected: Navigate to Pledges page. You should see a FilterBar with search input. Type a donor's first or last name and press Search. The table filters to pledges from contacts matching that name.
result: pass (re-test after fix 2672244 — search badge now displays)

### 7. Pledge Amount Range and Filters
expected: On Pledges page, the FilterBar includes Status dropdown, Frequency dropdown, Late toggle, date range, and amount range inputs. Enter a min amount — table filters to pledges >= that amount. Select a frequency (e.g. Monthly) — combined filters apply.
result: pass

### 8. Pledge Presets and CSV Export
expected: On Pledges page, click a preset (e.g. "Active", "Late Pledges"). Filters auto-apply. Click Export CSV — downloads a CSV of the currently filtered pledges.
result: pass (re-test after fix c4f1f2d — replaced duplicate Stalled preset with Active)

### 9. Journal Search and Archived Toggle
expected: Navigate to Journals page. You should see a FilterBar above the card grid (cards, not a table). Type a journal name in the search input and press Search — only matching journals appear. Click "Show Archived" toggle — archived journals appear. Button text changes to "Showing Archived".
result: pass (re-test after fix 5fdb479 — archived filter now correctly filters)

### 10. Journal Deadline Filter and Presets
expected: On Journals page, use the deadline date range inputs to set a from/to date. Journals filter by deadline. Click the "Has Deadline" preset — shows journals with upcoming deadlines. Click "Archived" preset — shows archived journals. Click Export CSV — downloads filtered journal CSV.
result: pass

### 11. URL Persistence Across Pages
expected: On Donations page, apply a few filters (e.g. type=One-time, amount_min=50). Copy the URL. Open a new tab and paste the URL. The page loads with the same filters applied and the same filtered results displayed.
result: pass

## Summary

total: 11
passed: 11
issues: 3 (all fixed and re-tested)
pending: 0
skipped: 0

## Gaps

[none yet]
