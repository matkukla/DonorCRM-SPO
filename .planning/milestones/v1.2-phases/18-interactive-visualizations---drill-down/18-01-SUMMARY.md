---
phase: 18-interactive-visualizations-drill-down
plan: 01
subsystem: admin-analytics
tags: [recharts, radix-ui, drill-down, interactive-charts, stage-filtering]
requires: [17-02]
provides: [funnel-drill-down, stage-contacts-endpoint]
affects: [18-02, 19-01]
tech-stack:
  added: []
  patterns: [recharts-onclick, conditional-fetching, slide-in-panel]
key-files:
  created:
    - apps/insights/tests/test_stage_contacts.py
    - frontend/src/pages/admin/analytics/components/FunnelDrilldownPanel.tsx
  modified:
    - apps/insights/services.py
    - apps/insights/serializers.py
    - apps/insights/views.py
    - apps/insights/urls.py
    - frontend/src/api/insights.ts
    - frontend/src/hooks/useInsights.ts
    - frontend/src/pages/admin/analytics/components/ConversionFunnelChart.tsx
    - frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx
decisions:
  - id: drill-down-state-local
    choice: Use local component state (useState) for drill-down UI
    rationale: Drill-downs are transient exploration actions that shouldn't be bookmarkable or shareable
    alternatives: [URL query params]
  - id: conditional-fetch-pattern
    choice: Use TanStack Query enabled option for conditional data fetching
    rationale: Prevents eager loading of drill-down data until panel opens, handles race conditions automatically
    pattern: "enabled: !!stage"
  - id: none-stage-handling
    choice: Use "none" string value for contacts with no stage events
    rationale: URL-friendly representation of null stage, consistent with backend filter logic
    implementation: "stage ?? 'none'"
metrics:
  duration: 5 minutes
  completed: 2026-02-15
---

# Phase 18 Plan 01: Funnel Stage Drill-Down Summary

**One-liner:** Interactive funnel chart with click-to-drill-down showing contacts in each pipeline stage via slide-in panel

## What Was Built

Built the funnel stage drill-down feature enabling admins to click any funnel chart segment and view the list of contacts currently in that pipeline stage. The drill-down panel slides in from the right without navigating away from the dashboard.

**Backend:**
- `get_stage_contacts(stage, limit)` service function filtering JournalContacts by current stage using Subquery pattern
- Handles "none" stage for contacts with no stage events (null current_stage)
- StageContactsView API endpoint at `/api/v1/insights/admin/stage-contacts/`
- Admin-only access enforcement (IsAdmin permission class)
- Comprehensive test suite covering access control, filtering, pagination, and edge cases

**Frontend:**
- ConversionFunnelChart enhanced with onClick handler calling parent callback with stage value
- FunnelDrilldownPanel component using Radix UI Sheet for slide-in panel
- Table display showing contact name, owner, last activity date
- Conditional data fetching using TanStack Query enabled option (only fetches when panel opens)
- AdminAnalyticsDashboard coordinates drill-down state (open/close, selected stage)

**Key Features:**
- Click any funnel stage segment to open drill-down panel
- Panel shows contact list filtered by pipeline stage
- Closes via Esc key, overlay click, or close button (Radix UI Dialog handles automatically)
- Loading state shows skeleton rows during data fetch
- Empty state shows "No contacts in this stage" message
- Stage label mapping (e.g., "contact" → "Contact")

## Deviations from Plan

None - plan executed exactly as written.

## Testing

**Backend tests (8 tests, all passing):**
- ✅ Admin can access endpoint (200)
- ✅ Non-admin gets 403 Forbidden
- ✅ Stage parameter is required (400 if missing)
- ✅ Returns contacts in correct stage
- ✅ Returns empty list for stage with no contacts
- ✅ "none" stage parameter returns contacts with no stage events
- ✅ Contact data structure includes required fields (id, full_name, email, owner_name, last_activity_date)
- ✅ Limit parameter restricts results

**Frontend verification:**
- ✅ TypeScript compilation succeeds with no errors
- ✅ Vite build succeeds

**Query performance:**
- Target: <5 queries per request
- Achieved: 4 queries (JournalContact with current_stage annotation, Contact with last_activity_date, owner select_related)

## Technical Decisions

**1. Recharts onClick Pattern**
- Used Recharts built-in onClick handler on Funnel component
- Callback signature: `(data: any, index: number, e: React.MouseEvent) => void`
- Data object contains all properties from chartData (name, value, percentage, stage)
- Added `cursor="pointer"` for visual feedback

**2. Conditional Fetching with TanStack Query**
- Pattern: `enabled: !!stage` prevents fetch when stage is null
- Prevents eager loading of drill-down data on initial page load
- Automatically refetches when stage changes (panel opened with new stage)
- Handles race conditions from rapid clicks (state replacement pattern)

**3. Radix UI Sheet for Slide-in Panel**
- Controlled mode: `open` prop + `onOpenChange` callback
- Handles keyboard navigation (Esc to close, Tab cycling) automatically
- Focus trapping and screen reader announcements built-in
- Override default width: `className="w-full sm:max-w-2xl"`

**4. Stage Value Handling**
- Backend: null for contacts with no stage events, PipelineStage enum values for others
- API: "none" string for null stage (URL-friendly)
- Frontend: `stage ?? 'none'` pattern for consistent handling
- Display: STAGE_LABELS map for human-readable names

## Commits

1. **77f2022** - `feat(18-01): add stage-contacts endpoint with tests`
   - Backend service, serializers, view, URL route, tests
   - Files: apps/insights/services.py, serializers.py, views.py, urls.py, tests/test_stage_contacts.py

2. **cfe0b01** - `feat(18-01): build interactive funnel chart and drill-down panel`
   - Frontend API types, hook, chart onClick, drill-down panel, dashboard state coordination
   - Files: frontend/src/api/insights.ts, hooks/useInsights.ts, ConversionFunnelChart.tsx, FunnelDrilldownPanel.tsx, AdminAnalyticsDashboard.tsx

## Next Phase Readiness

**Ready for Phase 18-02 (if planned):**
- Drill-down pattern established and reusable for other charts
- Conditional fetching pattern can be applied to user drill-down, time-series drill-down
- Sheet component configured and tested

**Considerations for future phases:**
- Add pagination controls to drill-down panel if contact lists exceed 100 (current limit)
- Add contact detail link from drill-down panel to contact detail page
- Consider adding sort controls to drill-down table
- Potential to add "View All" button linking to stalled contacts page with stage filter

**Architectural insights:**
- Local state works well for transient drill-downs (no URL complexity needed)
- Recharts onClick provides sufficient data access for drill-down triggers
- TanStack Query enabled option prevents performance issues from eager loading

## Documentation Updates

None required - feature is self-contained within analytics dashboard.

## Known Limitations

1. Drill-down panel shows first 100 contacts per stage (limit=100 default, max 500)
   - For stages with >100 contacts, user doesn't see full list
   - Future: Add pagination or "View All" link

2. No sorting controls in drill-down panel
   - Contacts appear in database order
   - Future: Add column headers with sort toggles

3. No direct navigation from drill-down contact to contact detail page
   - User must close panel and search for contact
   - Future: Make contact name clickable linking to `/contacts/:id`

4. Drill-down panel doesn't persist on page refresh
   - Transient state is lost
   - This is by design (local state), but could add URL state if needed

## Performance Notes

**Backend optimization:**
- Subquery annotation pattern keeps query count low (<5 queries)
- select_related('owner') prevents N+1 on owner lookups
- Distinct() on contact IDs prevents duplicates from multiple journal memberships

**Frontend optimization:**
- Conditional fetching prevents unnecessary API calls
- useMemo on chartData transformation prevents recalculation on every render
- Skeleton loading state provides perceived performance during data fetch

**Potential bottlenecks:**
- Large stages (>500 contacts) may cause slow response times
- No caching strategy for drill-down data (always fetches fresh)
- Consider adding staleTime or cacheTime tuning for drill-down queries if performance issues arise

---

*Completed: 2026-02-15*
*Duration: 5 minutes*
*Commits: 2*
*Tests Added: 8*
*Files Modified: 9*
