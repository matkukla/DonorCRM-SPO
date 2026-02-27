# Architecture Patterns: v2.2 Integration

**Domain:** Mission Supervisor role, journal report rebuild, Begin Prayer, dashboard modifications
**Researched:** 2026-02-26
**Confidence:** HIGH -- all features integrate with well-established existing patterns

## Recommended Architecture

v2.2 introduces five feature areas that touch different layers of the stack. The key architectural challenge is the Mission Supervisor role, which requires a new data relationship (supervisor-to-missionary assignment) and systematic queryset scoping changes across multiple apps. The other features are localized frontend component work that consumes existing APIs.

### Feature Integration Map

| Feature | Backend Changes | Frontend Changes | Data Model Changes |
|---------|----------------|------------------|--------------------|
| Mission Supervisor role | New UserRole, supervisor M2M, queryset scoping across 8+ views, permission updates, assignment API | Role in auth types, sidebar nav, role selector UI, assignment management UI | `SUPERVISOR` in UserRole, `supervised_users` M2M on User |
| Missionary dashboard selector | Add optional `user_id` param to DashboardView | New `MissionarySelector` component on Dashboard page | None |
| Journal report rebuild | New dedicated report endpoint on JournalAnalyticsViewSet | Replace 4 chart components in Reports tab with single `JournalReport` component | None |
| Begin Prayer | None (existing `focus/` and `prayed/` endpoints sufficient) | Expand `PrayerFocusMode.tsx` with Begin Prayer entry flow | None |
| Dashboard modifications | None | Modify `Dashboard.tsx` and tile sub-components | None |

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `User` model (extended) | Stores supervisor role + M2M assignment relationship | All owner-scoped views via queryset filtering |
| `supervised_users` M2M | Maps supervisors to their assigned missionaries | `User` model, all scoped querysets |
| `owner_scoped_filter()` helper | Returns Q object filtering data by user role + assignments | Contact, Gift, Journal, Prayer, Task, Dashboard, Insights views |
| `JournalAnalyticsViewSet.report()` (new) | Aggregates per-journal report data (metrics, stage distribution, decisions) | Frontend `JournalReport` component |
| `JournalReport.tsx` (new) | Renders key metrics, progress bar, charts, alerts | `useJournalReport` hook, Recharts |
| `MissionarySelector` component (new) | Dropdown for supervisors/admins to pick a missionary | Dashboard page, users API |
| `PrayerFocusMode.tsx` (modified) | Begin Prayer entry point and prayer session flow | `useTodaysFocus` hook, `useMarkPrayed` mutation |
| `Dashboard.tsx` (modified) | Layout changes, tile removal, chart toggle | Existing tile components, dnd-kit |

### Data Flow

#### Mission Supervisor Queryset Scoping

Current owner-scoping pattern (repeated across ~15 views):

```python
# Current pattern in contacts/views.py, journals/views.py, prayers/views.py, etc.
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        queryset = Model.objects.all()
    else:
        queryset = Model.objects.filter(owner=user)
    return queryset
```

New pattern adds supervisor scope:

```python
# Updated pattern
def get_queryset(self):
    user = self.request.user
    if user.role == 'admin':
        queryset = Model.objects.all()
    elif user.role == 'supervisor':
        supervised_ids = user.supervised_users.values_list('id', flat=True)
        queryset = Model.objects.filter(
            owner__in=[user.pk, *supervised_ids]
        )
    elif user.role in ['finance', 'read_only']:
        queryset = Model.objects.all()
    else:
        queryset = Model.objects.filter(owner=user)
    return queryset
```

**Extract to reusable helper** to avoid duplicating this logic in 15+ places:

```python
# apps/core/querysets.py (NEW FILE)
from django.db.models import Q


def owner_scoped_filter(user, owner_field='owner'):
    """
    Return Q object for owner-scoped filtering.

    - admin: no filter (sees all)
    - supervisor: own data + assigned missionaries' data
    - finance/read_only: no filter (sees all, write-gated by permissions)
    - staff: own data only
    """
    if user.role in ['admin', 'finance', 'read_only']:
        return Q()  # No filter -- sees everything

    if user.role == 'supervisor':
        supervised_ids = list(user.supervised_users.values_list('id', flat=True))
        return Q(**{f'{owner_field}__in': [user.pk] + supervised_ids})

    # staff -- own data only
    return Q(**{owner_field: user})
```

This helper returns a `Q` object so views can compose it with existing filters:

```python
# Usage in any view
def get_queryset(self):
    return Contact.objects.filter(
        owner_scoped_filter(self.request.user)
    ).select_related('owner')
```

For models where ownership is indirect (e.g., PrayerIntention via `contact__owner`, JournalStageEvent via `journal_contact__journal__owner`), pass the `owner_field` parameter:

```python
# Prayer intentions -- ownership via contact__owner
qs = PrayerIntention.objects.filter(
    owner_scoped_filter(request.user, owner_field='contact__owner')
)

# Journal views -- ownership via journal.owner
qs = Journal.objects.filter(
    owner_scoped_filter(request.user)
)

# Journal stage events -- deep ownership chain
qs = JournalStageEvent.objects.filter(
    owner_scoped_filter(request.user, owner_field='journal_contact__journal__owner')
)
```

#### Supervisor-Missionary Assignment Data Model

Use M2M on User rather than FK because:
1. A supervisor manages multiple missionaries (1-to-many on the supervisor side)
2. A missionary could theoretically be assigned to multiple supervisors (unlikely now, but M2M is zero-cost for the single-supervisor case and prevents future migration)
3. Self-referential M2M is cleaner than a separate junction model for this simple relationship

```python
# On User model
supervised_users = models.ManyToManyField(
    'self',
    symmetrical=False,
    related_name='supervisors',
    blank=True,
    help_text='Missionaries assigned to this supervisor'
)
```

Key decisions:
- `symmetrical=False` because the relationship is directional (supervisor -> missionary, not bidirectional)
- `related_name='supervisors'` allows `user.supervisors.all()` to find who supervises a given missionary
- The M2M table will be auto-generated as `users_user_supervised_users` by Django
- Only users with `role='supervisor'` should have `supervised_users` populated; enforce at the application/API level, not the model level
- Admin assignment UI manages the M2M; supervisors cannot self-assign

#### Dashboard Selector Flow

```
Supervisor/Admin clicks "View as [Missionary]" dropdown
  -> MissionarySelector dropdown renders
     - For supervisors: populated from user.supervised_users
     - For admins: populated from all staff users
  -> Selection sets selectedUserId state
  -> Dashboard API calls include ?user_id=<selectedUserId>
  -> Backend validates permission, calls get_dashboard_summary(target_user)
  -> Dashboard renders with missionary's data + "Viewing as X" banner
  -> "View My Dashboard" button clears selection, returns to own view
```

Backend approach: Add optional `user_id` parameter to `DashboardView.get()`:

```python
# apps/dashboard/views.py -- modified DashboardView
def get(self, request):
    user_id = request.query_params.get('user_id')
    if user_id:
        target_user = self._get_viewable_user(request.user, user_id)
        if target_user is None:
            return Response({'detail': 'Not authorized to view this user.'}, status=403)
        data = get_dashboard_summary(target_user)
    else:
        data = get_dashboard_summary(request.user)
    return Response(data)

def _get_viewable_user(self, requesting_user, target_user_id):
    """Return target user if requesting user has permission to view their dashboard."""
    if requesting_user.role == 'admin':
        return User.objects.filter(pk=target_user_id, is_active=True).first()
    elif requesting_user.role == 'supervisor':
        return requesting_user.supervised_users.filter(pk=target_user_id, is_active=True).first()
    return None
```

The existing `get_dashboard_summary(user)` already takes a user parameter and scopes all queries to that user. No changes needed to the service layer.

#### Journal Report Data Flow

```
JournalDetail.tsx (Reports tab)
  -> JournalReport component (NEW, replaces 4 chart components)
  -> useJournalReport(journalId) hook (NEW)
  -> GET /api/journals/analytics/report/?journal_id={id} (NEW endpoint)
  -> Server aggregates: total contacts, decisions, stage distribution, goal progress
  -> Returns single JournalReport response
  -> Component renders: 4 metric cards, progress bar, 2 Recharts charts, conditional alerts
```

The current Reports tab uses 4 separate API calls (decision-trends, stage-activity, pipeline-breakdown, next-steps-queue) via individual hooks. The rebuild replaces this with a single aggregated endpoint. Benefits:
1. Single network round-trip instead of 4
2. Server computes derived metrics (response rate, goal progress) atomically
3. Single loading/error state in the component

New backend endpoint on `JournalAnalyticsViewSet`:

```python
@action(detail=False, methods=['get'], url_path='report')
def report(self, request):
    """Per-journal report data for the rebuilt Reports tab."""
    journal_id = request.query_params.get('journal_id')
    if not journal_id:
        return Response({'detail': 'journal_id required'}, status=400)

    # Validate ownership/access (reuses existing pattern)
    try:
        if self._is_admin(request):
            journal = Journal.objects.get(pk=journal_id)
        elif request.user.role == 'supervisor':
            supervised_ids = request.user.supervised_users.values_list('id', flat=True)
            journal = Journal.objects.get(pk=journal_id, owner__in=[request.user.pk, *supervised_ids])
        else:
            journal = Journal.objects.get(pk=journal_id, owner=request.user)
    except Journal.DoesNotExist:
        return Response({'detail': 'Not found'}, status=404)

    # Build report data using existing ORM patterns
    report_data = build_journal_report(journal)
    return Response(report_data)
```

Response shape (matching spec from `prompts/journal_report.md`):

```python
{
    "journal": {
        "id": "uuid",
        "name": "Spring 2026 Support Raising",
        "goal_amount_cents": 500000,
        "deadline": "2026-06-30",
        "is_archived": False,
    },
    "summary": {
        "total_contacts": 45,
        "stalled_contacts": 3,
        "stage_distribution": {
            "contact": 10, "meet": 12, "close": 8,
            "decision": 5, "thank": 7, "next_steps": 3
        },
        "decisions": {
            "pending": 5,
            "confirmed": 20,
            "declined": 3,
            "canceled": 1,
            "confirmed_total_cents": 350000,
            "confirmed_monthly_equivalent_cents": 29166,
        },
        "goal_progress_percent": 70.0,
        "open_next_steps": 8,
        "overdue_next_steps": 2,
    }
}
```

#### Begin Prayer Flow

```
PrayerList page
  -> "Begin Prayer" button (NEW, prominent placement above prayer list)
  -> Fetches today's focus intentions via existing GET /api/prayers/focus/
  -> Opens PrayerFocusMode with fetched intentions
  -> User navigates through intentions, marking as prayed
  -> Each "Mark as Prayed" calls existing POST /api/prayers/{id}/prayed/
  -> Completion screen shows summary
  -> Return to PrayerList with invalidated prayer queries
```

No backend changes needed. The existing `TodaysFocusView` and `MarkPrayedView` endpoints provide all required functionality. This is purely a frontend UX change -- adding a prominent "Begin Prayer" button that launches the existing `PrayerFocusMode`.

## Patterns to Follow

### Pattern 1: Centralized Owner Scoping via Q Helper

**What:** Extract the repeated owner-scoping logic into `apps/core/querysets.py` with a `owner_scoped_filter()` function returning a `Q` object.

**When:** Every view that currently has the `if user.role in ['admin', 'finance', 'read_only']` pattern.

**Why:** Adding `supervisor` to 15+ views individually is error-prone. A central helper ensures consistency and makes future role changes one-line updates.

**Example:**
```python
# apps/core/querysets.py
from django.db.models import Q

def owner_scoped_filter(user, owner_field='owner'):
    if user.role in ['admin', 'finance', 'read_only']:
        return Q()
    if user.role == 'supervisor':
        supervised_ids = list(user.supervised_users.values_list('id', flat=True))
        return Q(**{f'{owner_field}__in': [user.pk] + supervised_ids})
    return Q(**{owner_field: user})
```

### Pattern 2: Role Hierarchy Extension

**What:** Add `supervisor` between `admin` and `finance` in the hierarchy.

**When:** Frontend `ProtectedRoute`, sidebar `canAccess`, role selector dropdowns.

**Current hierarchy:** `admin(4) > finance(3) > staff(2) > read_only(1)`

**New hierarchy:** `admin(5) > supervisor(4) > finance(3) > staff(2) > read_only(1)`

```typescript
// Frontend role hierarchy (ProtectedRoute.tsx, Sidebar.tsx)
const roleHierarchy: Record<string, number> = {
  admin: 5,
  supervisor: 4,
  finance: 3,
  staff: 2,
  read_only: 1,
}
```

```typescript
// Frontend types (api/users.ts, api/auth.ts)
export type UserRole = "admin" | "supervisor" | "staff" | "finance" | "read_only"

export const userRoleLabels: Record<UserRole, string> = {
  admin: "Administrator",
  supervisor: "Mission Supervisor",
  staff: "Staff",
  finance: "Finance",
  read_only: "Read Only",
}
```

### Pattern 3: Conditional Dashboard Banner

**What:** Show a "Viewing as [Missionary Name]" banner when supervisor/admin is viewing another user's dashboard, with a button to return to own view.

**When:** Dashboard page has a selected user ID that differs from the logged-in user.

```typescript
// Dashboard.tsx
function MissionarySelector({ selectedUserId, onSelect }: Props) {
  const { user } = useAuth()
  // For supervisors: fetch only their assigned users
  // For admins: fetch all staff users
  const { data: selectableUsers } = useSupervisedUsers()  // new hook

  if (user?.role !== 'admin' && user?.role !== 'supervisor') return null

  return (
    <div className="flex items-center gap-3">
      <Select value={selectedUserId ?? ""} onValueChange={onSelect}>
        <SelectTrigger><SelectValue placeholder="View missionary dashboard..." /></SelectTrigger>
        <SelectContent>
          {selectableUsers?.map(u => (
            <SelectItem key={u.id} value={u.id}>{u.full_name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {selectedUserId && (
        <Button variant="ghost" onClick={() => onSelect(undefined)}>
          View My Dashboard
        </Button>
      )}
    </div>
  )
}
```

### Pattern 4: Single Aggregated Report Endpoint

**What:** Replace 4 separate analytics API calls with one `GET /api/journals/analytics/report/?journal_id=X` endpoint.

**When:** Journal Reports tab.

**Why:** Reduces network round-trips from 4 to 1. Server computes derived metrics atomically. Single loading/error state.

### Pattern 5: Existing dnd-kit Tile System for Dashboard Changes

**What:** Dashboard tiles use `SortableDashboardTile` with `@dnd-kit/sortable` across three `SortableContext` zones (giving, stats, content). Modifications work within this system.

**How to remove a tile:** Remove its ID from the appropriate `DEFAULT_*_ORDER` array and its `case` in `renderTileById()`. Do NOT change the dnd-kit infrastructure.

**How to add chart toggle:** Add local state inside the tile's component (e.g., `MonthlyGiftsCard`), toggle between `<BarChart>` and `<LineChart>` from Recharts. The toggle control lives inside the card, not in the tile wrapper.

**How to make tiles "draggable anywhere":** Merge the three `SortableContext` zones into a single zone so tiles can move between sections. This changes the grid layout from three fixed grids to one unified grid.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Inline Role Checks in Every View

**What:** Adding `if user.role == 'supervisor'` individually to each of the 15+ views.

**Why bad:** Inconsistent application, missed views, hard to audit, guaranteed bugs when a view is forgotten.

**Instead:** Use the centralized `owner_scoped_filter()` Q helper. Refactor existing views to use it as part of the supervisor work, then the supervisor behavior comes free in every view that uses the helper.

### Anti-Pattern 2: Separate Supervisor Permission Class Per View

**What:** Creating `IsSupervisorOrAdmin` and adding it alongside existing permission classes on every view.

**Why bad:** Supervisor access is about data scoping (queryset filtering), not about endpoint access. A supervisor should access the same endpoints as staff -- they just see more data.

**Instead:** Keep existing permission classes (`IsAuthenticated`, `IsStaffOrAbove`, `IsAdmin`). Add `supervisor` to `IsStaffOrAbove`. The data scoping happens in `get_queryset()` via the Q helper, not in permission classes. Exception: Admin-only endpoints like admin analytics need a new check -- add `supervisor` to the allowed roles in `IsAdmin` or create `IsAdminOrSupervisor` for those specific endpoints.

### Anti-Pattern 3: Duplicating Dashboard for Supervisor View

**What:** Creating a separate `SupervisorDashboard.tsx` component or API endpoint.

**Why bad:** Code duplication, divergent behavior, double maintenance.

**Instead:** Reuse `Dashboard.tsx` and `DashboardView`. Add optional `user_id` parameter. The same component renders for all roles; supervisors/admins get an additional `MissionarySelector` dropdown.

### Anti-Pattern 4: Direct Checkbox Toggle Without Event Log

**What (from journal report spec):** "When a checkbox is clicked, the box should be checked directly instead of having to log an event."

**Why careful:** The current system logs stage events as append-only entries. Checkboxes in the grid represent "has this stage been completed" based on event history. Directly toggling without an event would break the audit trail.

**Instead:** When a checkbox is clicked, auto-create a stage event behind the scenes (using the existing `createStageEvent` mutation). The UI should optimistically check the box via React Query's `onMutate`, but the backend still gets its event log entry. This preserves the audit trail while giving the user instant visual feedback.

### Anti-Pattern 5: Building Report API from Scratch

**What:** Creating entirely new service functions for the journal report endpoint.

**Why bad:** The aggregation logic already exists in pieces across `JournalAnalyticsViewSet` methods.

**Instead:** Extract and compose existing query patterns. The new report endpoint reuses the same ORM queries but returns them in a single response. Specifically:
- Stage distribution: reuse the `pipeline_breakdown` subquery pattern (Subquery on JournalStageEvent ordered by `-created_at`)
- Decision counts: simple aggregate on Decision model filtered by journal
- Stalled contacts: reuse the 14-day stalled detection pattern from insights
- Next steps: count from NextStep model filtered by journal

## Integration Points: New vs Modified

### New Files

| File | Purpose |
|------|---------|
| `apps/core/querysets.py` | Centralized `owner_scoped_filter()` Q helper |
| `frontend/src/pages/journals/components/JournalReport.tsx` | Rebuilt report component with metrics, progress bar, charts, alerts |
| `frontend/src/components/dashboard/MissionarySelector.tsx` | User picker dropdown for supervisor/admin dashboard viewing |

### Modified Files (Backend)

| File | Change | Scope |
|------|--------|-------|
| `apps/users/models.py` | Add `SUPERVISOR` to UserRole, add `supervised_users` M2M, add `is_supervisor` property | Small (10-15 lines) |
| `apps/users/serializers.py` | Add `supervised_users` field to UserSerializer, expose in CurrentUserSerializer | Small |
| `apps/users/views.py` | New endpoint for managing supervisor assignments (add/remove assigned users) | Medium |
| `apps/users/urls.py` | Route for supervisor assignment management | Small |
| `apps/core/permissions.py` | Add `supervisor` to `IsStaffOrAbove`, consider `IsAdminOrSupervisor` for analytics | Small |
| `apps/contacts/views.py` | Refactor 6 views to use `owner_scoped_filter()` | Medium (mechanical) |
| `apps/journals/views.py` | Refactor 8 views to use `owner_scoped_filter()`, add `report` endpoint to viewset | Medium |
| `apps/prayers/views.py` | Refactor `_owner_scoped_queryset()` to use Q helper | Small |
| `apps/dashboard/views.py` | Add `user_id` parameter support to `DashboardView` | Small |
| `apps/dashboard/services.py` | No change (already takes `user` parameter) | None |
| `apps/insights/views.py` | Allow supervisors to access admin analytics endpoints, scope to their users | Medium |
| `apps/gifts/views.py` | Refactor owner scoping to use Q helper | Small |
| `apps/tasks/views.py` | Refactor owner scoping to use Q helper | Small |

### Modified Files (Frontend)

| File | Change | Scope |
|------|--------|-------|
| `frontend/src/api/auth.ts` | Add `supervisor` to `User.role` type | Small |
| `frontend/src/api/users.ts` | Add `supervisor` to `UserRole`, add `supervised_users` field, add role label | Small |
| `frontend/src/components/auth/ProtectedRoute.tsx` | Update role hierarchy (admin:5, supervisor:4, ...) | Small |
| `frontend/src/components/layout/Sidebar.tsx` | Update role hierarchy, show Admin nav for supervisors | Small |
| `frontend/src/pages/admin/AdminUsers.tsx` | Add `supervisor` to role selector, add supervisor assignment UI | Medium |
| `frontend/src/pages/Dashboard.tsx` | Remove journal activity tile, add chart toggle, add MissionarySelector, remove text, adjust spacing | Medium |
| `frontend/src/components/dashboard/GivingSummaryCard.tsx` | Remove "2026 calendar year" text | Small |
| `frontend/src/components/dashboard/MonthlyGiftsCard.tsx` | Remove "Updated today" text, add bar/line toggle | Small |
| `frontend/src/pages/journals/JournalDetail.tsx` | Replace 4 chart imports with single JournalReport, remove PipelineBreakdownChart | Small |
| `frontend/src/pages/journals/components/ReportCharts.tsx` | Delete or gut (replaced by JournalReport.tsx) | Delete |
| `frontend/src/pages/prayer/PrayerList.tsx` | Add "Begin Prayer" button | Small |
| `frontend/src/pages/prayer/PrayerFocusMode.tsx` | Minor UX enhancements for Begin Prayer entry | Small |
| `frontend/src/hooks/useJournals.ts` | Add `useJournalReport` hook | Small |
| `frontend/src/hooks/useUsers.ts` | Add hooks for supervised users and assignment management | Small |
| `frontend/src/App.tsx` | Update ProtectedRoute requiredRole for admin pages to allow supervisor | Small |

### Migration

One migration needed:
```
apps/users/migrations/XXXX_add_supervisor_role_and_m2m.py
- Add 'supervisor' to UserRole choices
- Add supervised_users M2M field
```

This is a non-destructive additive migration. No data transformation needed. The UserRole choices field is just a max_length CharField -- adding a new choice requires no schema change (the 'supervisor' string is 10 chars, within the existing `max_length=20`). The M2M creates a new junction table only.

## Views Requiring Queryset Scoping Update

Every view that currently performs owner scoping needs to support the supervisor role. Here is the complete inventory:

### Direct `owner` field

| View | File | Current Filter |
|------|------|---------------|
| `ContactListCreateView` | contacts/views.py:56 | `owner=user` |
| `ContactDetailView` | contacts/views.py:93 | `owner=user` |
| `ContactThankView` | contacts/views.py:120 | `owner=user` |
| `ContactSearchView` | contacts/views.py:239 | `owner=user` |
| `ContactEmailsView` | contacts/views.py:213 | `owner=user` |
| `JournalListCreateView` | journals/views.py:65 | `owner=user` |
| `JournalDetailView` | journals/views.py:121 | `owner=user` |

### Indirect owner via `contact__owner`

| View | File | Current Filter |
|------|------|---------------|
| `PrayerIntention views` | prayers/views.py:23 | `contact__owner=user` |
| `ContactGiftsView` | contacts/views.py:147 | `donor_contact__owner=user` |
| `ContactRecurringGiftsView` | contacts/views.py:170 | `donor_contact__owner=user` |
| `ContactTasksView` | contacts/views.py:197 | `owner=user` (task owner) |
| `ContactPrayerIntentionsView` | contacts/views.py:314 | `contact__owner=user` |

### Indirect owner via `journal__owner`

| View | File | Current Filter |
|------|------|---------------|
| `JournalStageEventListCreateView` | journals/views.py:166 | `journal_contact__journal__owner=user` |
| `JournalContactListCreateView` | journals/views.py:219 | `journal__owner=user` |
| `JournalContactDestroyView` | journals/views.py:263 | `journal__owner=user` |
| `DecisionListCreateView` | journals/views.py:300 | `journal_contact__journal__owner=user` |
| `DecisionDetailView` | journals/views.py:350 | `journal_contact__journal__owner=user` |
| `DecisionHistoryListView` | journals/views.py:380 | `decision__journal_contact__journal__owner=user` |
| `NextStepListCreateView` | journals/views.py:405 | `journal_contact__journal__owner=user` |
| `NextStepDetailView` | journals/views.py:436 | `journal_contact__journal__owner=user` |
| `JournalAnalyticsViewSet` (4 actions) | journals/views.py:456+ | `journal_contact__journal__owner=user` |
| `ContactJournalsView` | contacts/views.py:294 | `journal__owner=user` |
| `ContactJournalEventsView` | contacts/views.py:340 | `journal_contact__journal__owner=user` |

### Dashboard services (function parameter, not queryset filter)

| Function | File | Current Scoping |
|----------|------|----------------|
| `get_dashboard_summary()` | dashboard/services.py | Takes `user` param, scopes all sub-queries |
| `get_giving_summary()` | dashboard/services.py | Takes `user` param |
| `get_monthly_gifts()` | dashboard/services.py | Takes `user` param |
| All other dashboard service functions | dashboard/services.py | Takes `user` param |

Dashboard services already accept a user parameter. The supervisor dashboard selector only needs to pass the target user to these existing functions.

### Admin analytics (currently admin-only)

| View | File | Change Needed |
|------|------|--------------|
| `DashboardOverviewView` | insights/views.py:187 | Allow supervisor; scope to supervised users |
| `StalledContactsView` | insights/views.py:221 | Allow supervisor; scope to supervised users |
| `UserPerformanceView` | insights/views.py:271 | Allow supervisor; filter to supervised users |
| `ConversionFunnelView` | insights/views.py:290 | Allow supervisor; scope to supervised users |
| `TeamActivityView` | insights/views.py:324 | Allow supervisor; scope to supervised users |
| `TeamTrendsView` | insights/views.py:360 | Allow supervisor; scope to supervised users |
| `UserTrendsView` | insights/views.py:397 | Allow supervisor; validate target user is supervised |
| `UserJournalsView` | insights/views.py:425 | Allow supervisor; validate target user is supervised |
| `StageContactsView` | insights/views.py:451 | Allow supervisor; scope to supervised users |
| `UserDrilldownView` | insights/views.py:484 | Allow supervisor; validate target user is supervised |
| `ActivityHeatmapView` | insights/views.py:515 | Allow supervisor; scope to supervised users |

These currently use `IsAdmin` permission class. To support supervisors:
1. Replace `IsAdmin` with new `IsAdminOrSupervisor` permission class
2. The service functions currently operate on ALL data (no user scoping). For supervisors, add user filtering to the service calls. The cleanest approach: pass a `user_ids` parameter to service functions that filters to only those users' data.

## Suggested Build Order

Build order is driven by dependencies. The supervisor role touches the most files but does NOT block the other features.

### Phase 1: UI Polish (no backend changes, independent)

All dashboard and UI modification tasks:

1. Dashboard: remove "2026 calendar year" from GivingSummaryCard
2. Dashboard: remove "Updated today" from MonthlyGiftsCard
3. Dashboard: delete "Recent Journal Activity" tile (remove from `DEFAULT_CONTENT_ORDER` + `renderTileById`)
4. Dashboard: add bar/line chart toggle to MonthlyGiftsCard
5. Dashboard: adjust grid gaps (reduce `gap-6` to `gap-4` or similar)
6. Dashboard: make tiles draggable across sections (merge SortableContexts)
7. Rename "Prospect" to "Potential Donor" on contacts page
8. Remove Fund column from pledges page
9. Modify gifts page columns (remove Funds/Description, add Type)
10. Center modal dialogs
11. Remove Review Queue and heat map from analytics dashboard

**Rationale:** Zero risk, zero backend dependency, quick wins.

### Phase 2: Journal Report Rebuild (new component, new endpoint)

1. Create journal report backend endpoint (`JournalAnalyticsViewSet.report()`) with service function
2. Create `JournalReport.tsx` frontend component per spec
3. Replace Reports tab content in `JournalDetail.tsx`
4. Add `useJournalReport` hook
5. Delete old `ReportCharts.tsx` components (or keep as reference)
6. Implement checkbox direct-toggle behavior (auto-create stage event on click)

**Rationale:** Self-contained. New endpoint + new component. No interaction with other v2.2 features.

### Phase 3: Begin Prayer Feature (frontend only)

1. Add prominent "Begin Prayer" button to `PrayerList.tsx`
2. Wire button to fetch today's focus and open `PrayerFocusMode`
3. Any UX enhancements to the focus mode flow

**Rationale:** Pure frontend. Uses existing backend endpoints. Smallest scope.

### Phase 4: Mission Supervisor Role (largest, most complex)

1. Backend: Add SUPERVISOR role + M2M to User model + migration
2. Backend: Create `owner_scoped_filter()` helper in `apps/core/querysets.py`
3. Backend: Refactor ALL views to use the Q helper (see inventory above)
4. Backend: Update `IsStaffOrAbove` to include supervisor
5. Backend: Create `IsAdminOrSupervisor` for analytics endpoints
6. Backend: Add supervisor assignment management endpoint
7. Backend: Add `user_id` parameter to Dashboard API
8. Backend: Scope admin analytics service functions for supervisor filtering
9. Frontend: Update auth types, role hierarchy, sidebar nav
10. Frontend: Add supervisor to AdminUsers role selector + role badge variant
11. Frontend: Build supervisor assignment management UI in AdminUsers
12. Frontend: Build MissionarySelector component
13. Frontend: Wire Dashboard to use MissionarySelector + user_id param

**Rationale:** Most files touched, most complex. The Q helper refactor (steps 2-3) is the foundation -- it makes supervisor scoping automatic in every view. The refactor of existing views to use the Q helper is safe because it preserves identical behavior for existing roles.

**Phase ordering rationale:** Phases 1-3 can run in parallel or any order. Phase 4 must be last because the Q helper refactor in step 3 touches the same view files that Phase 2 may add an endpoint to. Doing Phase 4 last avoids merge conflicts.

## Scalability Considerations

| Concern | At 10-20 users | At 100 users | At 500 users |
|---------|---------------|--------------|--------------|
| M2M query for supervised_users | Negligible (5-15 supervised) | Still negligible | Still negligible |
| `__in` filter with supervised IDs | Fast (small list) | Fast | Fast -- PostgreSQL handles IN with 100 IDs trivially |
| Journal report aggregation | Fast (per-journal, bounded) | Same | Same -- bounded by journal member count, not total users |
| Dashboard with user_id | Same as current | Same | Same -- just different user parameter |
| Admin analytics for supervisor | One extra supervised_ids query | Same | Consider caching supervised_ids if >50 supervisors |

No scalability concerns for v2.2. The supervisor M2M adds one extra query per request (to fetch supervised IDs), which is negligible. The `owner_scoped_filter()` helper materializes the supervised_ids list once per request via `values_list('id', flat=True)`.

## Sources

- **Codebase analysis (HIGH confidence):**
  - `apps/users/models.py` -- User model, UserRole TextChoices
  - `apps/core/permissions.py` -- IsAdmin, IsStaffOrAbove, IsOwnerOrAdmin, IsContactOwnerOrReadAccess
  - `apps/contacts/views.py` -- Owner scoping patterns across 6 views
  - `apps/journals/views.py` -- Owner scoping patterns across 8+ views, JournalAnalyticsViewSet
  - `apps/prayers/views.py` -- _owner_scoped_queryset helper, TodaysFocusView, MarkPrayedView
  - `apps/dashboard/views.py` -- DashboardView with user parameter
  - `apps/dashboard/services.py` -- get_dashboard_summary and related functions
  - `apps/insights/views.py` -- 11 admin-only analytics endpoints
  - `frontend/src/pages/Dashboard.tsx` -- dnd-kit tile system, SortableContext zones
  - `frontend/src/pages/journals/JournalDetail.tsx` -- Reports tab with 4 chart components
  - `frontend/src/pages/journals/components/ReportCharts.tsx` -- Current chart implementations
  - `frontend/src/pages/prayer/PrayerFocusMode.tsx` -- Existing focus mode implementation
  - `frontend/src/pages/admin/AdminUsers.tsx` -- User management with role selectors
  - `frontend/src/components/auth/ProtectedRoute.tsx` -- Role hierarchy enforcement
  - `frontend/src/components/layout/Sidebar.tsx` -- Role-based navigation
  - `frontend/src/App.tsx` -- Route definitions with requiredRole guards
  - `frontend/src/api/auth.ts`, `frontend/src/api/users.ts` -- TypeScript role types
- **Spec documents (HIGH confidence):**
  - `prompts/mission_supervisor.md` -- Supervisor role requirements
  - `prompts/journal_report.md` -- Detailed report component spec
  - `prompts/dashboard_modification.md` -- Dashboard change list
- **Todo files (HIGH confidence):**
  - `.planning/todos/pending/2026-02-26-create-mission-supervisor-role.md`
  - `.planning/todos/pending/2026-02-26-rebuild-journal-report-component.md`
  - `.planning/todos/pending/2026-02-26-add-begin-prayer-feature-to-prayer-request-page.md`
  - `.planning/todos/pending/2026-02-26-modify-dashboard-layout-and-tile-content.md`

---
*Architecture research for: DonorCRM v2.2 -- Mission Supervisor, Journal Report, Begin Prayer & UI Polish*
*Researched: 2026-02-26*
