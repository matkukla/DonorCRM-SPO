---
status: resolved
phase: 19-advanced-features---export
source: 19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md
started: 2026-02-16T12:00:00Z
updated: 2026-02-16T12:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. DateRangePicker on Dashboard
expected: Navigate to /admin/analytics/dashboard. A DateRangePicker control appears in the page header area. Clicking it opens a popover with preset buttons (This Month, Last Month, Last Quarter, YTD, All Time) on the left and a dual-month calendar on the right.
result: pass

### 2. Date Range Filtering Updates Widgets
expected: On the Dashboard, select "This Month" preset from the DateRangePicker. All dashboard widgets (summary cards, trend chart, funnel chart, team activity table) should update to reflect only data from the current month. Selecting "All Time" reverts to unfiltered data.
result: pass

### 3. DateRangePicker on Stalled Contacts Page
expected: Navigate to /admin/analytics/stalled. A DateRangePicker control appears. Selecting a date range filters the stalled contacts list. Pagination resets to page 1 when date range changes.
result: pass

### 4. Export Stalled Contacts CSV
expected: On the Stalled Contacts page, click the "Export CSV" button. A CSV file downloads to your computer with filename containing the date range (e.g., stalled_contacts_2026-01-01_to_2026-02-16.csv). The file contains columns: Contact Name, Email, Owner, Last Activity Date, Days Stalled, Status.
result: pass

### 5. Export Team Activity CSV
expected: On the Dashboard, there is an Export CSV option for team activity data. Clicking it downloads a CSV file with columns: Date, User, Event Type, Title, Contact Name.
result: issue
reported: "I don't see the Export CSV option. Can you check again and verify that it is there?"
severity: major

### 6. Activity Heatmap
expected: On the Dashboard, below the team activity and alerts section, a GitHub-style activity heatmap calendar is visible. It shows colored squares representing daily activity density over the past year. A legend shows "Less" to "More" with color gradient from gray to green. Hovering/interacting with cells shows activity count.
result: issue
reported: "When I hover over the cells, activity count isn't shown"
severity: minor

### 7. Time Period Comparison
expected: On the Dashboard, a Time Period Comparison section appears. When a date range is selected, it shows the current period vs. a matching prior period side-by-side. Four metrics displayed: Total Contacts, Conversion Rate, Stalled Contacts, and Donations. Each metric shows trend arrows (green up, red down, gray neutral) with percentage change.
result: pass

### 8. User Comparison
expected: On the Dashboard, a User Comparison section appears with two dropdown selectors. Selecting two different missionaries shows 5 metrics side-by-side: Total Contacts, Active Journals, Decisions Logged, Conversion Rate, Total Donations. The higher value in each metric is highlighted in green. You cannot select the same user in both dropdowns.
result: pass

### 9. Heatmap Respects Date Filter
expected: Select a date range (e.g., "Last Quarter") from the DateRangePicker on the Dashboard. The Activity Heatmap updates to show only the selected date range rather than the default 365 days.
result: pass

### 10. Invalid Date Handling
expected: If you manually construct a URL with invalid date params (e.g., ?date_from=not-a-date), the API returns a 400 error with a helpful message rather than crashing. The UI handles this gracefully.
result: issue
reported: "does not return any error"
severity: minor

## Summary

total: 10
passed: 7
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "Export CSV button exists for team activity data on the Dashboard, clicking it downloads a CSV"
  status: resolved
  reason: "User reported: I don't see the Export CSV option. Can you check again and verify that it is there?"
  severity: major
  test: 5
  root_cause: "useExportTeamActivity hook and backend endpoint exist but no Export CSV button was added to TeamActivityTable component"
  artifacts:
    - path: "frontend/src/pages/admin/analytics/components/TeamActivityTable.tsx"
      issue: "Missing Export CSV button — hook exists but never wired to UI"
  missing:
    - "Import useExportTeamActivity hook and Download icon"
    - "Add Export CSV button in CardHeader matching StalledContacts pattern"
    - "Pass dateParams to export mutation"
- truth: "Hovering over heatmap cells shows activity count tooltip"
  status: resolved
  reason: "User reported: When I hover over the cells, activity count isn't shown"
  severity: minor
  test: 6
  root_cause: "ActivityHeatmap component missing rectRender prop required for tooltips in @uiw/react-heat-map"
  artifacts:
    - path: "frontend/src/pages/admin/analytics/components/ActivityHeatmap.tsx"
      issue: "No rectRender prop — library requires it for custom tooltip rendering"
  missing:
    - "Add rectRender prop to HeatMap component with tooltip showing date and count"
    - "Use existing shadcn/ui Tooltip component for consistent styling"
- truth: "Invalid date params in URL return 400 error with helpful message"
  status: resolved
  reason: "User reported: does not return any error"
  severity: minor
  test: 10
  root_cause: "Frontend never reads date params from URL — dateRange is component state only, so invalid URL params are silently ignored"
  artifacts:
    - path: "frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx"
      issue: "dateRange initialized from useState(null), no URL query param reading"
  missing:
    - "Read date_from/date_to from URL search params on mount"
    - "Validate URL params and show error or initialize dateRange state"
    - "Optional: sync URL when DateRangePicker changes"
