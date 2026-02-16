---
phase: 15-frontend-foundation-routing
plan: 02
subsystem: ui
tags: [react, typescript, react-query, react-router-dom, tailwind, radix-ui]

# Dependency graph
requires:
  - phase: 15-01
    provides: React Query hooks for admin analytics endpoints (useAdminDashboardOverview, useAdminStalledContacts, useAdminUserPerformance, useAdminConversionFunnel)
  - phase: 14-02
    provides: Backend endpoints with typed responses (DashboardOverviewResponse, StalledContactsResponse, UserPerformanceResponse, ConversionFunnelResponse)
provides:
  - 3 functional admin analytics page components with real API data
  - Reusable admin sub-navigation pattern
  - Loading state, error state handling pattern for data pages
  - Currency and date formatting utilities for admin analytics
affects: [16-analytics-visualizations, 17-analytics-interactivity]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Admin sub-navigation tabs (Users, Import Center, Analytics) with NavLink active state
    - Loading skeleton placeholders matching AdminUsers pattern
    - Error message display with retry prompts
    - Currency formatting (cents to dollars) using toLocaleString
    - Date formatting using toLocaleDateString with readable format

key-files:
  created: []
  modified:
    - frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx
    - frontend/src/pages/admin/analytics/StalledContacts.tsx
    - frontend/src/pages/admin/analytics/UserDetail.tsx

key-decisions:
  - "Use simple HTML table for conversion funnel instead of premature Recharts visualization (Phase 16 will add charts)"
  - "UserDetail page filters client-side from useAdminUserPerformance data (backend returns all users in one response)"
  - "Days stalled badge uses 3 color variants: destructive >30, warning >14, secondary otherwise"

patterns-established:
  - "Admin analytics pages follow consistent structure: admin sub-nav → loading state → error state → data display"
  - "Summary cards use CardHeader with text-sm font-medium text-muted-foreground for metric name, CardContent with text-2xl font-bold for value"
  - "Pagination info shown as 'Showing X of Y' below tables (full pagination controls deferred to Phase 17)"

# Metrics
duration: 3m
completed: 2026-02-13
---

# Phase 15 Plan 02: Admin Analytics Pages Summary

**3 functional admin analytics pages rendering real API data with loading/error states, admin sub-navigation, and data-first foundation for Phase 16-17 visualizations**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-13T23:06:15Z
- **Completed:** 2026-02-13T23:08:53Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- AdminAnalyticsDashboard page displays 4 summary cards (Total Contacts, Active Journals, Stalled Contacts, Conversion Rate), donations card, and conversion funnel table using real API data
- StalledContacts page displays table of stalled contacts with 5 columns (Contact Name, Owner, Last Activity, Days Stalled badge, Status) and pagination info
- UserDetail page displays 6 metric cards for a specific user (Total Contacts, Active Journals, Decisions Logged, Conversion Rate, Total Donations, Donation Count) with user-not-found handling
- All pages include admin sub-navigation tabs matching AdminUsers pattern
- All pages handle loading states with skeleton placeholders and error states with retry prompts

## Task Commits

Each task was committed atomically:

1. **Task 1: Build AdminAnalyticsDashboard page with real data** - `8b0ed84` (feat)
2. **Task 2: Build StalledContacts and UserDetail pages with real data** - `8decc64` (feat)

## Files Created/Modified
- `frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx` - Displays dashboard overview with summary cards, donations card, and conversion funnel table. Uses useAdminDashboardOverview and useAdminConversionFunnel hooks.
- `frontend/src/pages/admin/analytics/StalledContacts.tsx` - Displays stalled contacts table with sorting defaults (days_stalled desc). Uses useAdminStalledContacts hook with StalledContactsParams.
- `frontend/src/pages/admin/analytics/UserDetail.tsx` - Displays user-specific metrics extracted from useAdminUserPerformance data by URL :id param. Handles user-not-found case with error message and back link.

## Decisions Made
- **Conversion funnel visualization:** Used simple HTML table instead of Recharts for initial foundation. Phase 16 will replace with proper funnel chart visualization. This keeps Phase 15 focused on data rendering and routing.
- **UserDetail data loading:** UserDetail page calls useAdminUserPerformance (which returns all users) and filters client-side by :id param. This matches the backend endpoint design where user performance is returned as a list, not a per-user endpoint.
- **Badge color variants:** Days stalled uses 3-tier color system: destructive for >30 days (critical), warning for >14 days (needs attention), secondary otherwise. Handles null days_stalled with "N/A" text display.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 16 (Analytics Visualizations):**
- All 3 admin analytics pages render real data from backend endpoints
- Data structures are typed and rendering correctly
- Loading/error states handle edge cases gracefully
- Admin sub-navigation provides consistent context across admin section
- Foundation is data-first: Phase 16 can enhance with Recharts visualizations without modifying data layer

**Ready for Phase 17 (Analytics Interactivity):**
- StalledContacts has basic sorting defaults in place (sort_by: days_stalled, sort_dir: desc)
- Pagination info is displayed ("Showing X of Y")
- UserDetail has back navigation to dashboard
- Full interactive sorting controls, pagination controls, and filters can be added incrementally

**No blockers or concerns.**

---
*Phase: 15-frontend-foundation-routing*
*Completed: 2026-02-13*
