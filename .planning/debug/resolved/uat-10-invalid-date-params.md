---
status: diagnosed
trigger: "Diagnose root cause for UAT issue #10: Invalid date params in URL return 400 error with helpful message vs User reported: does not return any error"
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T00:00:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: Frontend ignores URL query parameters for date filtering and uses component state only, so invalid URL params never reach the backend
test: Read AdminAnalyticsDashboard.tsx and trace how dates are passed to API calls
expecting: No code reading date_from/date_to from URL query params
next_action: Read AdminAnalyticsDashboard.tsx to examine DateRangePicker integration

## Symptoms

expected: Invalid date params in URL return 400 error with helpful message
actual: Does not return any error
errors: None
reproduction: Manually add ?date_from=not-a-date to the browser URL
started: Always broken (UAT testing)

## Eliminated

## Evidence

- timestamp: 2026-02-16T00:05:00Z
  checked: AdminAnalyticsDashboard.tsx lines 22-23
  found: dateRange state initialized to null, converted to params via dateRangeToParams(dateRange)
  implication: Date filtering is entirely driven by component state, not URL query params

- timestamp: 2026-02-16T00:06:00Z
  checked: date-presets.ts lines 59-70
  found: dateRangeToParams returns empty object {} when range is null, otherwise returns {date_from, date_to} formatted as YYYY-MM-DD
  implication: Params sent to API are controlled by DateRangePicker component state, not URL

- timestamp: 2026-02-16T00:07:00Z
  checked: views.py lines 213-227 (DashboardOverviewView)
  found: Backend validates date_from/date_to params and returns 400 with error message for invalid format
  implication: Backend validation works correctly IF invalid params reach it

- timestamp: 2026-02-16T00:08:00Z
  checked: insights.ts lines 309-313 (getAdminDashboardOverview function)
  found: Function passes params object directly to apiClient.get(..., { params })
  implication: Only params passed explicitly to the function are sent to API

- timestamp: 2026-02-16T00:09:00Z
  checked: useInsights.ts lines 97-102 (useAdminDashboardOverview hook)
  found: Hook passes DashboardOverviewParams from argument to getAdminDashboardOverview(params)
  implication: Only the params passed to the hook (derived from component state) are sent to API

## Resolution

root_cause: Frontend never reads date params from URL query string — date filtering is entirely driven by component state (dateRange from useState). When user manually adds ?date_from=invalid to URL, the frontend ignores it and sends either empty params {} or valid params from DateRangePicker state, so backend validation never triggers.
fix: N/A (research only)
verification: N/A (research only)
files_changed: []
