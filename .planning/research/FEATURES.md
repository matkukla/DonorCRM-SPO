# Feature Research: v2.2 UI Polish, Journal Report, Mission Supervisor & Begin Prayer

**Domain:** Donor CRM for missionaries -- UI refinement, role expansion, prayer workflow, report rebuild
**Researched:** 2026-02-26
**Confidence:** HIGH (all features are internal refinements of existing codebase; no new external dependencies)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that address existing UX friction or complete partially-built capabilities. Missing these means the product feels unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Center all modal dialogs | Dialogs should appear centered on screen. The `dialog.tsx` primitive already uses `left-[50%] top-[50%] translate-x/y-[-50%]` centering. Issue likely in custom dialog-like components or Sheet-based panels not using the standard Dialog primitive. | LOW | Audit all 7 DialogContent consumers across pages (AdminUsers, PrayerList, GroupList, AddContactsDialog, CreateJournalDialog, LogEventDialog, DecisionDialog). Verify each uses the standard `DialogContent` from `@/components/ui/dialog.tsx`. |
| Rename "Prospect" to "Potential Donor" | Domain language mismatch -- missionaries don't think in sales terms like "prospect." Currently appears in 3 frontend files as display labels in `statusLabels` maps. | LOW | Frontend-only change: update `statusLabels` maps in ContactList.tsx (lines 32, 264), ContactForm.tsx (line 20), ContactDetail.tsx (line 43). Backend `ContactStatus.PROSPECT = 'prospect', 'Prospect'` display label can optionally change too (one migration). The stored value `'prospect'` stays unchanged. |
| Remove Fund/Description columns from gifts page | Simplifies the gifts list view per user request. Columns defined at DonationList.tsx lines 102-122 (`fund_name` and `description`). | LOW | Delete 2 column definitions from `columns` array. Add a "Type" column if the Gift model has a `gift_type` field (it does -- from RE import `Gift Type` column). Keep fund filter in FilterBar (still useful for filtering even without column display). |
| Remove Fund column from pledges page | Same simplification rationale. Pledges page has a fund column to remove. | LOW | Delete 1 column definition from pledges list page. |
| Remove Review Queue and heatmap from analytics dashboard | User request. Review Queue endpoint (`ReviewQueueView`) and Activity Heatmap (`ActivityHeatmapView`) are both admin-only analytics features to be removed from the UI. | LOW | Remove `ActivityHeatmap` and `ReviewQueue`-related imports and JSX from `AdminAnalyticsDashboard.tsx`. Leave backend endpoints in place (non-breaking). Consider removing `@uiw/react-heat-map` from package.json if no other consumer exists. |
| Dashboard text cleanup | Remove "2026 calendar year" from GivingSummaryCard footer (line 135), "Updated today" from MonthlyGiftsCard footer (line 104), and "Recent Journal Activity" tile entirely. | LOW | Delete specific footer text lines. Remove `RecentJournalActivity` from imports, `DEFAULT_CONTENT_ORDER`, and `renderTileById` switch case in Dashboard.tsx. Remove the `RecentJournalActivity` component import. |
| Dashboard gap resizing | Large visual gaps between dashboard tile sections make the page feel sparse. Current spacing uses `gap-6` and `gap-8` with `space-y-8` between sections. | LOW | Reduce gap values (e.g., `gap-4` instead of `gap-6`, `space-y-6` instead of `space-y-8`). Purely CSS change. |

### Differentiators (Competitive Advantage)

Features that set DonorCRM apart. These address the unique missionary fundraising and supervision workflow.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Mission Supervisor role with scoped visibility | Supervisors see only their assigned missionaries' data. Admins see all. Both can select a missionary and view their personal dashboard. Standard CRMs offer all-or-nothing admin access. This provides fine-grained organizational hierarchy support. | HIGH | See detailed breakdown in Technical Notes section below. Requires model changes (new role, M2M relationship), new permission class, modification of 13+ admin-only API endpoints, and frontend missionary selector. |
| Begin Prayer dedicated session | Expands existing Focus Mode (PrayerFocusMode.tsx) into a richer guided prayer experience. Current Focus Mode is a carousel that steps through intentions with mark-as-prayed. "Begin Prayer" adds a dedicated entry point, session framing, and enhanced completion experience. | MEDIUM | Current PrayerFocusMode has: full-screen overlay, card carousel, keyboard navigation (arrows, P/Enter, Space, Esc), mark-as-prayed with auto-advance, completion screen with prayed count. "Begin Prayer" extends with: dedicated button in TodaysFocus component, optional session timer/duration, richer completion summary. Backend: no new models needed if session stats stay client-side; optional PrayerSession model for persistence. |
| Journal report rebuild | Complete redesign of journal reporting with 4 metric cards, goal progress bar, stage bar chart, and decision donut chart. Replaces existing DecisionTrends, StageActivity, PipelineBreakdown, and NextStepsQueue charts. Detailed spec in prompts/journal_report.md. | MEDIUM | New `JournalReport.tsx` component using existing report API. Key sections: (1) 4 metric cards in 2x2/4x1 responsive grid -- Total Contacts, With Decisions (response rate), Confirmed ($ with goal %), Pending Decisions. (2) Goal progress bar with animated fill. (3) Contacts by Stage bar chart with specific hex colors per stage. (4) Decision Status donut chart (inner/outer radius). (5) Conditional alert sections for stalled contacts and open next steps. |
| Stage checkbox direct-check behavior | Currently clicking an empty stage checkbox opens LogEventDialog for manual event logging. New behavior: clicking directly logs the event (marks stage as done) without dialog. Dialog accessible via other interaction for adding notes. | MEDIUM | Modify StageCell.tsx click handler to call stage event creation API directly instead of opening LogEventDialog. Requires a "quick log" API call (POST with minimal payload: stage, contact, journal). The existing `onCellClick` callback chain needs restructuring: quick-click = auto-log, some other gesture (e.g., clicking filled checkbox) = open timeline/dialog for notes. |
| Dashboard chart toggle (bar vs line) | MonthlyGiftsCard currently shows only BarChart. Toggle lets users switch to LineChart for trend visualization. Standard pattern in analytics dashboards. | LOW | Add `chartType` state to MonthlyGiftsCard. Conditionally render Recharts `BarChart`/`Bar` or `LineChart`/`Line` component. Both use same data format (`months` array with `total` and `short_label` keys). Add small toggle button group (BarChart3/LineChart icons from lucide-react) in CardHeader. |
| Dashboard drag anywhere (cross-section) | Current dashboard has 3 separate SortableContext sections (giving, stats, content) restricting drag to within each section. Users want to drag any tile to any position. | MEDIUM | Two approaches: (1) Flatten all tiles into single SortableContext with unified responsive grid -- simpler but loses distinct section layouts (2-col, 4-col, 2-col). (2) Keep sections but add cross-container drag logic with dnd-kit's `useDroppable` on each section. Approach 1 recommended: single flat list with responsive CSS grid, tiles self-size based on content. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Supervisor can edit missionary data | "Supervisors need to help fix data issues" | Breaks ownership model. Complex permission edge cases (who owns edits? audit trail confusion). Supervisor role is for VIEWING, not editing. | Supervisor views data read-only. Admin handles edits, or missionary fixes their own data. |
| Persistent dashboard tile order | "I rearranged tiles and lost them on refresh" | Requires user preferences model, API endpoints, migration. Explicitly out of scope in PROJECT.md. | Keep session-only tile ordering. Minor annoyance vs. infrastructure cost. |
| Real-time prayer session sync | "Multiple people praying for same intentions" | No WebSocket infrastructure. Prayer is personal. Multi-user sync adds complexity without value. | Client-side sessions. Last-prayed-at syncs via REST on completion. |
| Supervisor self-assignment | "Let supervisors pick who they oversee" | Breaks admin control over org structure. Supervisors could access unauthorized data. | Admin-only assignment of missionaries to supervisors. |
| Dynamic column visibility toggle | "Let users pick columns to show/hide" | UI complexity, state management, user confusion. Most users want same columns. | Curate correct defaults per page (the v2.2 column changes). Revisit if real need emerges. |
| Backend-stored "Potential Donor" label | "Change the database value from 'prospect' to 'potential_donor'" | Requires data migration of all contacts with status='prospect', updates to serializers, API contract change, potential client breakage. | Change display label only (frontend maps + TextChoices display string). Keep `'prospect'` as stored value. |

## Feature Dependencies

```
Mission Supervisor Role
    |-- requires --> UserRole.SUPERVISOR addition (model + migration)
    |-- requires --> User.supervised_missionaries M2M (model + migration)
    |-- requires --> IsSupervisorOrAdmin permission class
    |-- requires --> Scoped service functions (insights app, 13+ endpoints)
    |-- requires --> Missionary selector UI (frontend dropdown)
    |-- enables  --> "View as missionary" dashboard

Journal Report Rebuild
    |-- requires --> Existing report API (already built)
    |-- coupled with --> Stage checkbox behavior change (both are journal UX)
    |-- independent of --> Mission Supervisor, Begin Prayer

Begin Prayer
    |-- requires --> Existing PrayerFocusMode (already built)
    |-- requires --> Existing prayer API (already built)
    |-- independent of --> Journal Report, Mission Supervisor

Dashboard Modifications (text, gaps, chart toggle, drag anywhere)
    |-- requires --> Existing Dashboard.tsx (already built)
    |-- independent of --> All other features

UI Polish (dialog centering, column changes, label rename)
    |-- independent of --> All other features
    |-- parallelizable with --> Everything
```

### Dependency Notes

- **Mission Supervisor requires model changes first:** M2M relationship and role choice must be migrated before permission classes or view changes can reference them. Backend before frontend.
- **Journal report and checkbox behavior are coupled:** Both modify the journal detail page experience. Should be in same phase to avoid duplicate testing of journal page.
- **UI Polish has zero dependencies:** All items (dialog centering, label rename, column removals, dashboard text cleanup) can be done in any order and in parallel with larger features.
- **Begin Prayer extends but does not replace Focus Mode:** Current PrayerFocusMode is the base. Begin Prayer wraps it with session context. Backward-compatible enhancement.
- **Dashboard modifications are self-contained:** Chart toggle, gap resizing, drag-anywhere, and text removal are all within Dashboard.tsx and its child components. No backend changes.

## Implementation Phases

### Phase 1: UI Polish (Low-Risk, Quick Wins)

Simple frontend-only changes with no backend impact. Ship first.

- [ ] Remove "2026 calendar year" text from GivingSummaryCard
- [ ] Remove "Updated today" text from MonthlyGiftsCard
- [ ] Remove "Recent Journal Activity" tile from Dashboard
- [ ] Rename "Prospect" to "Potential Donor" in ContactList, ContactForm, ContactDetail
- [ ] Remove Fund and Description columns from gifts page; add Type column
- [ ] Remove Fund column from pledges page
- [ ] Remove Review Queue and heatmap from analytics dashboard
- [ ] Audit and fix any non-centered dialog usages

### Phase 2: Dashboard Enhancements

Moderate frontend changes to dashboard layout and interaction.

- [ ] Add bar/line chart toggle to MonthlyGiftsCard
- [ ] Reduce dashboard gap/spacing for tighter layout
- [ ] Implement cross-section tile dragging (flatten to single SortableContext)

### Phase 3: Journal Report Rebuild + Checkbox Behavior

Complete replacement of journal report and grid interaction change. Coupled because both modify the journal detail page.

- [ ] Create new JournalReport.tsx with 4 metric cards (Total Contacts, With Decisions, Confirmed $, Pending)
- [ ] Add progress-toward-goal bar with animated fill
- [ ] Add contacts-by-stage bar chart (6 stages, specific hex colors)
- [ ] Add decision-status donut chart (pending/confirmed/declined/canceled)
- [ ] Add conditional alert sections (stalled contacts, open next steps)
- [ ] Remove PipelineBreakdown chart from report
- [ ] Change stage checkbox click to directly log event (skip LogEventDialog)
- [ ] Ensure dialog still accessible for adding notes (e.g., click filled checkbox)

### Phase 4: Begin Prayer

Enhancement to existing prayer feature.

- [ ] Add "Begin Prayer" button/entry point to prayer page or TodaysFocus
- [ ] Enhance PrayerFocusMode with session framing (optional timer/duration display)
- [ ] Create richer completion summary (total time, per-intention breakdown)
- [ ] Decide on persistence: client-side only vs. PrayerSession model

### Phase 5: Mission Supervisor Role

Highest complexity. Backend model changes, permission expansion, frontend.

- [ ] Add `SUPERVISOR = 'supervisor', 'Supervisor'` to UserRole TextChoices + migration
- [ ] Add `supervised_missionaries = models.ManyToManyField('self', symmetrical=False, related_name='supervisors', blank=True)` to User model + migration
- [ ] Create `IsSupervisorOrAdmin` permission class that checks role and M2M assignment
- [ ] Modify insights service functions to accept optional `user_ids` filter parameter for scoping queries to assigned missionaries only
- [ ] Update all 13 admin-only views in insights app to use `IsSupervisorOrAdmin` and pass scoped user list to services
- [ ] Add missionary selector dropdown to admin analytics dashboard (shared between supervisor and admin)
- [ ] Add "view as missionary" to personal dashboard: load another user's dashboard data via `?user_id=` API parameter
- [ ] Admin UI for assigning missionaries to supervisors (UserDetail or dedicated page)
- [ ] Frontend route guard updates: supervisor can access /admin/analytics but not /admin (user management)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Dashboard text cleanup | MEDIUM | LOW | P1 |
| Rename Prospect to Potential Donor | MEDIUM | LOW | P1 |
| Remove Fund/Description columns (gifts) | MEDIUM | LOW | P1 |
| Remove Fund column (pledges) | LOW | LOW | P1 |
| Remove Review Queue + heatmap (analytics) | MEDIUM | LOW | P1 |
| Center dialogs | LOW | LOW | P1 |
| Chart toggle (bar/line) | MEDIUM | LOW | P1 |
| Dashboard gap resize | MEDIUM | LOW | P1 |
| Dashboard drag anywhere | MEDIUM | MEDIUM | P2 |
| Journal report rebuild | HIGH | MEDIUM | P1 |
| Stage checkbox direct-check | HIGH | MEDIUM | P1 |
| Begin Prayer session | MEDIUM | MEDIUM | P2 |
| Mission Supervisor role | HIGH | HIGH | P1 |

**Priority key:**
- P1: Must have for v2.2 milestone
- P2: Should have, include if schedule permits

## Existing Code Impact Analysis

### Backend Changes Required

| Feature | Models | Views | Serializers | Permissions | Services | Migrations |
|---------|--------|-------|-------------|-------------|----------|------------|
| Mission Supervisor | User (role + M2M) | 13+ insights views | User serializer | New IsSupervisorOrAdmin | All insights services | Yes (2) |
| Begin Prayer | Optional PrayerSession | Optional session endpoints | Optional | None | None | Optional |
| Journal checkbox | None | None | None | None | None | None |
| Rename Prospect label | ContactStatus display | None | None | None | None | Optional (1) |
| All other UI polish | None | None | None | None | None | None |

### Frontend Changes Required

| Feature | Pages | Components | Hooks | API Client | Types |
|---------|-------|------------|-------|------------|-------|
| Dashboard mods | Dashboard.tsx | GivingSummaryCard, MonthlyGiftsCard, SortableDashboardTile | None | None | None |
| Column removals | DonationList.tsx, PledgeList (pledges page) | None | None | None | None |
| Dialog centering | Up to 7 dialog consumers | dialog.tsx (verify) | None | None | None |
| Label rename | ContactList, ContactForm, ContactDetail | None | None | None | None |
| Analytics removal | AdminAnalyticsDashboard.tsx | ActivityHeatmap, ReviewQueue refs | None | None | None |
| Chart toggle | None | MonthlyGiftsCard.tsx | None | None | None |
| Journal report | JournalDetail.tsx | New JournalReport.tsx, modify StageCell.tsx, remove old ReportCharts | useJournals hooks | journals.ts (maybe) | journal types |
| Begin Prayer | PrayerList.tsx | New or modified PrayerFocusMode | usePrayers hooks | prayers.ts (optional) | prayer types |
| Mission Supervisor | AdminAnalyticsDashboard.tsx, Dashboard.tsx | New MissionarySelector, route guards | useInsights, useUsers | insights.ts, users.ts | User types |

## Technical Notes

### Mission Supervisor -- Scoped Visibility Pattern

The existing codebase uses role-based scoping in two patterns:

**1. Service-level scoping** (e.g., `_scope_gifts(user)` in `apps/insights/services.py`):
```python
def _scope_gifts(user):
    if user.role in ['admin', 'finance', 'read_only']:
        return Gift.objects.all()
    return Gift.objects.filter(donor_contact__owner=user)
```
This must be extended for SUPERVISOR: query all gifts where `donor_contact__owner__in=user.supervised_missionaries.all()`.

**2. View-level permission** (`IsAdmin` in `apps/core/permissions.py`):
```python
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
```
Must become `IsSupervisorOrAdmin` checking `role in ['admin', 'supervisor']`. For supervisor, must also verify the requested user_id (if any) is in their supervised_missionaries set.

**Why M2M not FK:** `supervised_missionaries = ManyToManyField('self', symmetrical=False)` because:
- One supervisor oversees multiple missionaries (5-15 typical)
- One missionary could have multiple supervisors (team lead + regional director)
- symmetrical=False because A supervises B does not mean B supervises A
- Admin assigns via M2M add/remove, clean Django admin integration

**All 13 admin-only views that need modification:**
1. DashboardOverviewView
2. StalledContactsView
3. UserPerformanceView
4. ConversionFunnelView
5. TeamActivityView
6. TeamTrendsView
7. UserTrendsView
8. UserJournalsView
9. StageContactsView
10. UserDrilldownView
11. ActivityHeatmapView (being removed from UI but endpoint stays)
12. ReviewQueueView (being removed from UI but endpoint stays)
13. CSV export views in `export_views.py`

### Journal Report -- Checkbox Behavior Change

**Current flow:** Click empty stage cell -> `onCellClick` fires -> Opens LogEventDialog -> User fills event type + notes -> API POST creates stage event -> Cell refreshes with checkmark.

**Desired flow:** Click empty stage cell -> API POST auto-creates stage event with default type -> Cell refreshes with checkmark immediately. No dialog.

Implementation: StageCell's `handleClick` calls a new "quick log" function that POSTs `{ stage, contact_id, journal_id, event_type: 'completed' }` directly. The existing `onCellClick` prop is repurposed or a new `onQuickLog` prop added. For adding notes after the fact, clicking a FILLED checkbox could open the EventTimelineDrawer where notes can be added to the existing event.

### Dashboard Drag Anywhere -- Architecture Decision

Current Dashboard.tsx structure:
```tsx
<DndContext>
  <SortableContext items={givingOrder}>    {/* 2 items, lg:grid-cols-2 */}
  <SortableContext items={statsOrder}>     {/* 4 items, lg:grid-cols-4 */}
  {/* MPD section - NOT draggable */}
  <SortableContext items={contentOrder}>   {/* 5 items, lg:grid-cols-2 */}
</DndContext>
```

**Recommended approach:** Flatten into single SortableContext. Unified array of all tile IDs. Single responsive grid (e.g., `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`). Each tile spans columns based on its type via `col-span-*` classes. This gives full drag freedom while maintaining visual hierarchy through CSS.

**Alternative (if section separation is important):** Keep 3 SortableContexts but modify `handleDragEnd` to detect cross-section moves and transfer items between arrays. More complex, preserves distinct section grids.

### "View as Missionary" Dashboard

For supervisor/admin to see a missionary's personal dashboard:
- Add `?user_id=<uuid>` query parameter to dashboard API endpoint
- Backend: if requester is admin, return that user's data. If supervisor, verify user_id is in supervised_missionaries, then return that user's data. If staff, ignore parameter (own data only).
- Frontend: missionary selector dropdown at top of Dashboard page (visible to admin/supervisor only). Selecting a missionary appends `?user_id=` to API calls.
- All existing dashboard service functions (`get_dashboard_summary`, `get_donations_by_month`, etc.) already accept a `user` parameter -- just need to resolve the target user from the query param.

## Sources

- Existing codebase analysis (all files cited inline) -- HIGH confidence
- Feature specs from `prompts/mission_supervisor.md`, `prompts/journal_report.md`, `prompts/dashboard_modification.md` -- HIGH confidence (direct user requirements)
- DonorCRM `.planning/PROJECT.md` for constraints, current state, out-of-scope items -- HIGH confidence
- `.planning/codebase/ARCHITECTURE.md` for permission and scoping patterns -- HIGH confidence
- `.planning/EDGE_CASE_AUDIT.md` for known journal system issues -- HIGH confidence
- Existing component code: `dialog.tsx`, `PrayerFocusMode.tsx`, `StageCell.tsx`, `Dashboard.tsx`, `AdminAnalyticsDashboard.tsx`, `GivingSummaryCard.tsx`, `MonthlyGiftsCard.tsx`, `DonationList.tsx` -- HIGH confidence (direct source reading)

---
*Feature research for: DonorCRM v2.2 UI Polish, Journal Report, Mission Supervisor & Begin Prayer*
*Researched: 2026-02-26*
*Confidence: HIGH (all features reference existing codebase with exact file/line locations; specs from user prompts)*
