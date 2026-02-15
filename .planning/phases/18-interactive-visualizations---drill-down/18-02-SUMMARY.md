---
phase: 18-interactive-visualizations-drill-down
plan: 02
subsystem: admin-analytics
tags: [radix-ui, slide-in-panel, user-drilldown, conditional-fetching, quick-view]
requires: [18-01]
provides: [user-drilldown-endpoint, user-drilldown-panel]
affects: [19-01]
tech-stack:
  added: []
  patterns: [conditional-fetching, slide-in-panel, cents-to-dollars-formatting]
key-files:
  created:
    - apps/insights/tests/test_user_drilldown.py
    - frontend/src/pages/admin/analytics/components/UserDrilldownPanel.tsx
  modified:
    - apps/insights/services.py
    - apps/insights/serializers.py
    - apps/insights/views.py
    - apps/insights/urls.py
    - frontend/src/api/insights.ts
    - frontend/src/hooks/useInsights.ts
    - frontend/src/pages/admin/analytics/components/TeamActivityTable.tsx
    - frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx
decisions:
  - id: cents-storage-dollars-display
    choice: Store donations in cents (backend), display as dollars (frontend)
    rationale: Follows existing pattern for currency handling; cents prevent float precision issues
    implementation: "(amount / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' })"
  - id: quick-view-vs-navigation
    choice: Quick View button opens slide-in panel instead of navigating to detail page
    rationale: Enables rapid inspection without losing dashboard context
    alternatives: [direct navigation to /admin/analytics/users/{id}]
  - id: stalled-count-in-drilldown
    choice: Include stalled contact count as highlighted stat in drilldown panel
    rationale: Most actionable metric for coaching decisions; visual prominence drives attention
    implementation: "Amber border and text when count > 0"
metrics:
  duration: 9 minutes
  completed: 2026-02-15
---

# Phase 18 Plan 02: User Drilldown Panel Summary

**One-liner:** Quick View button on Team Activity Table opens slide-in panel with user stats, stalled contacts, and recent journals

## What Was Built

Built the User Drilldown Panel feature enabling admins to click "Quick View" on any Team Activity Table row and see a quick summary of that missionary's performance without leaving the dashboard.

**Backend:**
- `get_user_drilldown(user_id)` service function aggregating user stats, stalled count, and recent journals
- Reuses existing query patterns from `get_user_performance` for per-user metrics
- UserDrilldownView API endpoint at `/api/v1/insights/admin/user-drilldown/`
- Admin-only access enforcement (IsAdmin permission class)
- Returns 404 for non-existent user, 400 for missing user_id parameter
- `get_team_activity` enhanced to include `user_id` field for drill-down button
- Comprehensive test suite (7 tests, all passing)

**Frontend:**
- TeamActivityTable enhanced with conditional "Quick View" button column (Eye icon)
- UserDrilldownPanel component using Radix UI Sheet for slide-in panel
- Key stats grid showing total contacts, active journals, decisions, conversion rate, donations, stalled contacts
- Recent journals table (top 5) with progress indicators (active/total members, decisions)
- Stalled contacts highlighted in amber when count > 0
- Link to full User Detail page for deeper analysis
- AdminAnalyticsDashboard coordinates both funnel and user drilldown panels
- Conditional data fetching using TanStack Query enabled option (only fetches when panel opens)

**Key Features:**
- Click "Quick View" button to open user drill-down panel
- Panel shows user info (name, email, role) and 6 key stats
- Donations formatted from cents to dollars with locale formatting
- Stalled contacts card has amber border/text when > 0 (visual prominence)
- Recent journals show active/total member ratio and decision count
- Empty state for users with no active journals
- Loading state shows skeleton blocks during data fetch
- Panel closes via Esc key, overlay click, or programmatic close

## Deviations from Plan

None - plan executed exactly as written.

## Testing

**Backend tests (7 tests, all passing):**
- ✅ Admin can access endpoint (200)
- ✅ Non-admin gets 403 Forbidden
- ✅ User_id parameter required (400 if missing)
- ✅ Returns correct stats for user (contacts, journals, decisions, conversion rate, donations)
- ✅ Returns stalled contact count (contacts with >14 days since last activity)
- ✅ Returns recent journals with progress indicators (member_count, decision_count, active_member_count)
- ✅ Returns 404 for non-existent user

**Frontend verification:**
- ✅ TypeScript compilation succeeds with no errors
- ✅ Vite build succeeds

**Query performance:**
- Target: <15 queries per request
- Achieved: ~12 queries (user fetch, contact counts, journal counts, decision counts, donation aggregation, stalled calculation, recent journals with annotations)

## Technical Decisions

**1. Conditional Fetching Pattern**
- Pattern: `enabled: !!userId` prevents fetch when userId is null
- Prevents eager loading of drill-down data on initial page load
- Automatically refetches when userId changes (panel opened with new user)
- Consistent with funnel drill-down pattern from 18-01

**2. Currency Display (Cents to Dollars)**
- Backend stores donations in cents (Decimal field)
- Frontend converts to dollars: `(amount / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' })`
- Follows existing pattern from AdminAnalyticsDashboard donations display
- Prevents float precision issues with currency calculations

**3. Stalled Contacts Visual Prominence**
- Amber border and text color when stalled_contacts > 0
- Tailwind classes: `border-amber-500 bg-amber-50/50 dark:bg-amber-950/20`
- Most actionable metric for coaching decisions
- Drives admin attention to missionaries needing support

**4. Quick View vs. Direct Navigation**
- Quick View opens slide-in panel (transient exploration)
- Link to full detail page available in panel for deeper analysis
- Enables rapid inspection without losing dashboard context
- User can open multiple drill-downs in sequence without back/forward navigation

**5. Column Stability with useMemo**
- Columns array memoized based on `onUserDrilldown` presence
- Prevents column re-creation on every render
- Conditional "Actions" column only added when callback provided
- Follows React best practices for table performance

## Commits

1. **e74f7d5** - `feat(18-02): add user-drilldown endpoint with tests`
   - Backend service, serializers, view, URL route, tests
   - Updated get_team_activity to include user_id field
   - Files: apps/insights/services.py, serializers.py, views.py, urls.py, tests/test_user_drilldown.py

2. **ea58183** - `feat(18-02): build user drilldown panel and wire to team activity table`
   - Frontend API types, hook, Quick View button, drill-down panel, dashboard state coordination
   - Files: frontend/src/api/insights.ts, hooks/useInsights.ts, TeamActivityTable.tsx, UserDrilldownPanel.tsx, AdminAnalyticsDashboard.tsx

## Next Phase Readiness

**Ready for Phase 19 (Alerts & Coaching Insights):**
- User drilldown pattern established for rapid inspection
- Stalled contacts visualization ready for alert escalation
- Conditional fetching pattern reusable for other drill-downs
- Sheet component configured and tested for slide-in panels

**Considerations for future phases:**
- Add drill-down from AlertsPanel to relevant users (reuse UserDrilldownPanel)
- Consider adding "Email User" quick action in drill-down panel
- Potential to add filtering/sorting to journals table in panel
- Add pagination controls if journal list exceeds 5 (current limit)

**Architectural insights:**
- Conditional fetching pattern prevents performance issues from eager loading
- Cents-to-dollars conversion at display time maintains data integrity
- Visual prominence (amber highlighting) effectively drives admin attention
- Slide-in panels work well for transient exploration without navigation overhead

## Documentation Updates

None required - feature is self-contained within analytics dashboard.

## Known Limitations

1. Drill-down panel shows first 5 non-archived journals
   - For users with >5 journals, user doesn't see full list
   - Future: Add "View All Journals" link or pagination

2. No sorting controls in journals table
   - Journals appear in reverse chronological order (newest first)
   - Future: Add column headers with sort toggles

3. No direct actions from drill-down panel
   - Cannot email user, create task, or flag for coaching
   - Future: Add quick action buttons for common workflows

4. Drill-down panel doesn't persist on page refresh
   - Transient state is lost (by design)
   - This matches funnel drill-down behavior (local state pattern)

5. Stalled contact count calculated at query time
   - Not cached; recalculated on every drill-down open
   - For very large contact lists, might cause latency
   - Future: Consider caching or precomputing if performance issues arise

## Performance Notes

**Backend optimization:**
- Reuses existing query patterns from get_user_performance for consistency
- Subquery annotation pattern for last_activity_date prevents N+1
- select_related and annotate keep query count low (<15 queries)
- Stalled calculation uses same Subquery pattern as get_stalled_contacts

**Frontend optimization:**
- Conditional fetching prevents unnecessary API calls
- useMemo on columns array prevents recalculation on every render
- Skeleton loading state provides perceived performance during data fetch
- Currency formatting happens at render time (minimal overhead)

**Potential bottlenecks:**
- Users with very large contact counts may see slow stalled calculation
- No caching strategy for drill-down data (always fetches fresh)
- Consider adding staleTime tuning if performance issues arise

---

*Completed: 2026-02-15*
*Duration: 9 minutes*
*Commits: 2*
*Tests Added: 7*
*Files Modified: 9*
