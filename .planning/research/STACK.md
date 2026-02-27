# Technology Stack: v2.2 Additions

**Project:** DonorCRM v2.2 -- UI Polish, Journal Report Rebuild & Mission Supervisor Role
**Researched:** 2026-02-26
**Confidence:** HIGH

## Summary

v2.2 requires **zero new dependencies** -- no new npm packages, no new Python packages. Every feature (Mission Supervisor role, missionary dashboard selector, journal report rebuild with bar/donut charts and progress bars, Begin Prayer expansion, chart toggle) is fully achievable with the already-installed stack. This was verified by examining every installed package version and every existing usage pattern in the codebase.

---

## Existing Stack (DO NOT re-research, DO NOT re-install)

| Layer | Technology | Version | v2.2 Relevance |
|-------|-----------|---------|----------------|
| Backend | Django 4.2.28 + DRF | 4.2.28 / 3.14+ | Supervisor role, M2M assignment, scoped querysets |
| Frontend | React 19 + TypeScript + Vite | 19.2.0 / 5.9.3 / 7.2.4 | All UI features |
| Database | PostgreSQL + Django ORM | UUID PKs, TimeStampedModel | User M2M relationship |
| UI | Tailwind 3.4 + Radix UI | Various | All component styling |
| Charts | Recharts | 3.6.0 | Journal report bar/donut, dashboard chart toggle |
| Progress | @radix-ui/react-progress | 1.1.8 | Journal report goal progress bar |
| Select | @radix-ui/react-select | 2.2.6 | Missionary dashboard selector |
| Checkbox | @radix-ui/react-checkbox | 1.3.3 | Journal report direct-check behavior |
| Dialog | @radix-ui/react-dialog | 1.1.15 | Modal centering fix, prayer UI |
| Data | TanStack Query + TanStack Table | 5.90.17 / 8.21.3 | Data fetching, table rendering |
| Filtering | django-filter 24.3 + nuqs | Pinned | URL state for missionary selector |
| Auth | JWT (simplejwt) + role-based | 5.3+ | Role extension for supervisor |
| DnD | @dnd-kit/core + sortable | 6.3.1 / 10.0.0 | Dashboard tile reordering (already works) |
| Icons | lucide-react | 0.562.0 | Chart toggle icons, prayer icons |
| Dates | date-fns | 4.1.0 | Journal report date formatting |

---

## Feature-by-Feature Stack Analysis

### 1. Mission Supervisor Role -- Django model + permission changes (NO new dependency)

**What's needed:** New `SUPERVISOR` role value, M2M relationship for supervisor-to-missionary assignments, scoped queryset filtering across all views.

| Component | Technology | Pattern Source |
|-----------|-----------|----------------|
| New role enum | `UserRole.SUPERVISOR = 'supervisor'` added to `TextChoices` | Follows existing `STAFF/ADMIN/FINANCE/READ_ONLY` in `apps/users/models.py:13-20` |
| Supervisor-missionary M2M | `ManyToManyField('self', symmetrical=False)` on User model | Similar to `PrayerIntention.gifts` M2M pattern |
| Scoped querysets | Extend existing role checks in `get_queryset()` across all view files | Pattern already in every view: contacts, journals, gifts, tasks, prayers, insights |
| Permission classes | New `IsSupervisorOrAdmin` or extend `IsAdmin` | Follows existing `IsFinanceOrAdmin`, `IsStaffOrAbove` in `apps/core/permissions.py` |
| Serializer/admin | Add `supervised_users` to `UserAdminUpdateSerializer` | Follows existing admin update pattern in `apps/users/serializers.py` |

**Why M2M on User model (not a FK):**

A supervisor oversees multiple missionaries, and a missionary could theoretically have multiple supervisors. `ManyToManyField('self', symmetrical=False, related_name='supervisors', blank=True)` creates an auto-generated join table. This is more flexible than adding a `supervisor` FK on User, which would limit each missionary to one supervisor.

**Why NOT a separate assignment model with metadata:**

The relationship is simple -- user-to-user with no extra data (no "assigned_date" or "role within supervision" needed). Django's built-in M2M join table is sufficient. If metadata is needed later, the M2M can be refactored to use a `through` model without breaking the API.

**Queryset scoping pattern (exists in every view, add one `elif`):**

```python
# Current pattern in apps/contacts/views.py:56-68
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        qs = Contact.objects.all()
    else:
        qs = Contact.objects.filter(owner=user)

# v2.2 extension -- add supervisor between admin and staff:
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        qs = Contact.objects.all()
    elif user.role == 'supervisor':
        qs = Contact.objects.filter(
            owner__in=user.supervised_users.all()
        )
    else:
        qs = Contact.objects.filter(owner=user)
```

**Views that need the supervisor elif (verified count: ~25 get_queryset methods):**

| App | File | Methods |
|-----|------|---------|
| contacts | `views.py` | 10 `get_queryset()` methods |
| contacts | `export_views.py` | 1 queryset method |
| journals | `views.py` | 11 `get_queryset()` methods |
| journals | `export_views.py` | 1 queryset method |
| gifts | `views.py` | Multiple queryset methods |
| tasks | `views.py` | Multiple queryset methods |
| prayers | `views.py` | Multiple queryset methods |
| insights | `views.py` | Admin analytics endpoints |

**Mixin approach to reduce repetition:**

```python
# apps/core/mixins.py
class ScopedQuerysetMixin:
    """Mixin for owner-scoped querysets with supervisor support."""
    owner_field = 'owner'  # Override in views where FK is different

    def get_scoped_queryset(self, base_qs):
        user = self.request.user
        if user.role in ['admin', 'finance', 'read_only']:
            return base_qs
        elif user.role == 'supervisor':
            return base_qs.filter(
                **{f'{self.owner_field}__in': user.supervised_users.all()}
            )
        return base_qs.filter(**{self.owner_field: user})
```

**Should supervisors see their OWN data too?** Per the spec ("same access as Admin but can only see missionaries under them"), supervisors see ONLY their assigned missionaries' data, not their own (unless they are assigned to themselves). The admin does the assignment, so they can add the supervisor to their own list if needed. This avoids special-casing.

**Confidence:** HIGH -- Django `ManyToManyField('self')` is documented since Django 1.0. The queryset scoping pattern is proven across 25+ view methods in this codebase.

### 2. Missionary Dashboard Selector -- Radix Select + nuqs (NO new dependency)

**What's needed:** A dropdown on the Dashboard page allowing supervisors and admins to select a missionary and view their dashboard data.

| Component | Technology | Why This Exact Technology |
|-----------|-----------|--------------------------|
| Selector dropdown | `@radix-ui/react-select` v2.2.6 | Already used for every dropdown in the app (role selector in AdminUsers, filter selectors in FilterBar). Accessible, keyboard-navigable, styled via shadcn/ui. |
| Selected user state | `nuqs` URL param `?viewing_user=<uuid>` | App convention: all filter state lives in URL params via nuqs. Makes selection bookmarkable, shareable, survives page refresh. Used in FilterBar, analytics dashboard. |
| User list data | New API endpoint or extend `/api/users/` | Returns missionaries the current user can view. Supervisors get their assigned list; admins get all staff users. |
| Dashboard data | Existing `/api/dashboard/summary/` with `?user_id=<uuid>` param | Backend validates requesting user has permission to view target user's data. |

**Frontend implementation pattern:**

```tsx
// In Dashboard.tsx - add at top alongside existing useAuth
import { useQueryState } from 'nuqs'

const { user } = useAuth()
const canSelectUser = user?.role === 'admin' || user?.role === 'supervisor'

const [viewingUserId, setViewingUserId] = useQueryState('viewing_user')

// Pass to dashboard data hook
const { data } = useDashboardSummary({ user_id: viewingUserId || undefined })
```

**Backend validation pattern:**

```python
# In dashboard view
def get(self, request):
    target_user_id = request.query_params.get('user_id')
    if target_user_id:
        if request.user.role == 'admin':
            pass  # Admin can view anyone
        elif request.user.role == 'supervisor':
            if not request.user.supervised_users.filter(id=target_user_id).exists():
                raise PermissionDenied("Cannot view this user's dashboard")
        else:
            raise PermissionDenied("Only admins and supervisors can view other dashboards")
```

**Why NOT a separate "impersonation" system:** The missionary selector only changes what dashboard data is displayed. It does not change the authenticated user or their permissions. This is "viewing someone's data with permission" not "acting as someone else." Simpler, safer, no session manipulation needed.

**Confidence:** HIGH -- Follows exact patterns already in the codebase (admin owner filter on contacts page uses same Radix Select + query param pattern).

### 3. Journal Report Rebuild -- Recharts + Radix Progress (NO new dependency)

**What's needed:** New component with 4 metric cards, progress bar toward goal, bar chart (contacts by stage), donut chart (decision status), checkbox direct-check behavior, removal of Pipeline Breakdown and extra decision column.

Every chart type and UI component is already installed and used in this codebase:

| Report Element | Component | Already Used In |
|---------------|-----------|----------------|
| Bar chart (contacts by stage) | `recharts` `BarChart` + `Bar` + `Cell` | `MonthlyGiftsCard.tsx`, `ReportCharts.tsx` DecisionTrendsChart |
| Donut chart (decision status) | `recharts` `PieChart` + `Pie` with `innerRadius` | `GivingSummaryCard.tsx` lines 80-94 (exact donut pattern) |
| Progress bar (goal progress) | `@radix-ui/react-progress` | `components/ui/progress.tsx` (installed, component exists) |
| Chart container + theming | `ChartContainer` + `ChartTooltip` | `components/ui/chart.tsx` (shadcn/ui wrapper) |
| Metric cards | `Card` + `CardContent` + `CardHeader` | Used in dashboard StatCards, analytics cards |
| Checkbox (direct-check) | `@radix-ui/react-checkbox` | Used in journal grid already |

**Donut chart pattern (already proven in `GivingSummaryCard.tsx`):**

```tsx
// Exact pattern from GivingSummaryCard.tsx:80-94 -- reuse for decision status donut
<PieChart>
  <Pie
    data={donutData}
    dataKey="value"
    innerRadius={60}    // Creates the donut hole
    outerRadius={90}
    paddingAngle={2}
    startAngle={90}
    endAngle={-270}
    strokeWidth={0}
  >
    {donutData.map((entry, index) => (
      <Cell key={index} fill={entry.fill} />
    ))}
  </Pie>
</PieChart>
```

**Progress bar with inner label (extend existing component):**

The existing `@radix-ui/react-progress` component at `components/ui/progress.tsx` provides the accessible base (Root + Indicator with `translateX` transform). The journal report spec calls for showing the confirmed amount text inside the bar. This can be done by composing the existing component with an absolutely-positioned label:

```tsx
// No new component needed -- compose inline
<div className="relative">
  <Progress value={progressPercent} className="h-8" />
  {progressPercent >= 15 && (
    <span className="absolute inset-0 flex items-center justify-end pr-2 text-white text-sm font-medium">
      {formatCurrency(confirmedAmount)}
    </span>
  )}
</div>
```

**Checkbox direct-check behavior change:**

The current journal grid requires logging a stage event (opens `LogEventDialog`) when a checkbox is clicked. The v2.2 spec says "whenever a checkbox is clicked, the box should be checked instead of having to log an event." This means:

1. Clicking a stage checkbox directly creates a stage event via the existing API (no dialog)
2. Uses existing `@radix-ui/react-checkbox` component
3. Calls existing stage event creation mutation, just skips the dialog step
4. This is a behavior change in the journal grid component, not a stack change

**API data structure (already exists):**

The existing `GET /api/journals/{id}/report/` endpoint returns:
- `journal.goalAmountCents` -- for progress bar denominator
- `summary.decisions.confirmedTotalCents` -- for progress bar numerator
- `summary.stageDistribution` -- for bar chart data
- `summary.decisions.{pending, confirmed, declined, canceled}` -- for donut chart data
- `summary.goalProgressPercent` -- computed percentage

No API changes needed for the report rebuild. The data structure already contains every field referenced in the `prompts/journal_report.md` spec.

**Confidence:** HIGH -- Every chart type verified as already in use in this codebase with the exact Recharts 3.6.0 API.

### 4. Begin Prayer Expansion -- Pure component work (NO new dependency)

**What's needed:** Expand the existing Focus Mode with a dedicated "Begin Prayer" entry point and enhanced session flow.

The existing `PrayerFocusMode.tsx` (243 lines) is a complete, polished focus mode with:
- Full-screen amber overlay (`fixed inset-0 z-50`)
- Card-by-card prayer intention display
- Forward/backward navigation with keyboard shortcuts (Arrow keys, Space, Enter, P, Esc)
- "Mark as Prayed" mutation via `useMarkPrayed` hook
- Prayer count tracking in session state
- Completion screen with summary
- Empty state handling

**What "Begin Prayer" adds (all achievable with existing stack):**

| Addition | Technology | Notes |
|----------|-----------|-------|
| "Begin Prayer" button on Prayer page | Existing `Button` component + React state | New entry point, triggers existing `PrayerFocusMode` |
| Prayer session view/page | Existing fullscreen overlay pattern | Could be a dedicated route or reuse the overlay |
| Session summary | React state (already tracks `prayedIds`) | Already built in completion screen |
| Today's focus filtering | Existing `TodaysFocus.tsx` component | Already filters active intentions |

**No technology gaps.** The "Begin Prayer" feature is a UX entry point expansion -- a new button placement and potentially a streamlined flow into the existing Focus Mode. The `PrayerFocusMode` component does all the heavy lifting already.

**Confidence:** HIGH -- Verified by reading every line of `PrayerFocusMode.tsx` and `TodaysFocus.tsx`.

### 5. Dashboard Chart Toggle (Bar vs Line) -- Recharts conditional render (NO new dependency)

**What's needed:** A toggle on the Monthly Gifts card to switch between BarChart and LineChart views of the same data.

Both chart types are already imported and used in the codebase:

| Chart Type | Already Used In | Import Statement |
|------------|----------------|-----------------|
| `BarChart` + `Bar` | `MonthlyGiftsCard.tsx` (current view) | `from "recharts"` |
| `LineChart` + `Line` | `UserDetail.tsx`, `TrendCharts.tsx` | `from "recharts"` |

**The data shape is identical.** Both BarChart and LineChart consume the same `data.months` array with `total` dataKey. Switching between them is a conditional render, not a data transformation.

**Toggle UI recommendation -- simple button pair (no new component):**

```tsx
// In MonthlyGiftsCard.tsx
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts"
import { BarChart3, TrendingUp } from "lucide-react"  // Already installed

const [chartType, setChartType] = useState<"bar" | "line">("bar")

// In CardHeader, alongside title:
<div className="flex items-center gap-1">
  <button
    onClick={() => setChartType("bar")}
    className={cn("p-1.5 rounded", chartType === "bar" ? "bg-muted" : "hover:bg-muted/50")}
  >
    <BarChart3 className="h-4 w-4" />
  </button>
  <button
    onClick={() => setChartType("line")}
    className={cn("p-1.5 rounded", chartType === "line" ? "bg-muted" : "hover:bg-muted/50")}
  >
    <TrendingUp className="h-4 w-4" />
  </button>
</div>

// In chart area:
{chartType === "bar" ? (
  <BarChart data={data.months}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="short_label" ... />
    <YAxis ... />
    <ChartTooltip ... />
    <Bar dataKey="total" fill="var(--color-total)" radius={[4, 4, 0, 0]} />
    {/* ReferenceLine for goal */}
  </BarChart>
) : (
  <LineChart data={data.months}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="short_label" ... />
    <YAxis ... />
    <ChartTooltip ... />
    <Line dataKey="total" stroke="var(--color-total)" strokeWidth={2} dot={{ r: 3 }} />
    {/* ReferenceLine for goal */}
  </LineChart>
)}
```

**Why NOT Radix ToggleGroup:** Not installed (`@radix-ui/react-toggle-group` is not in `package.json`). Simple styled buttons with `cn()` conditional classes achieve the same result with zero new dependencies. The toggle has only two options -- a toggle group is overkill.

**Why NOT Radix Tabs:** Semantically, tabs imply switching between different content panels. A chart type toggle is switching visualization of the SAME data. Button pair is more semantically correct.

**Confidence:** HIGH -- BarChart and LineChart share identical Recharts API for XAxis/YAxis/CartesianGrid/ReferenceLine. Only the data series component differs (Bar vs Line).

---

## What NOT to Add

| Package | Why You Might Think You Need It | Why You Don't |
|---------|-------------------------------|---------------|
| `@radix-ui/react-toggle-group` | Chart toggle UI | Two buttons with `cn()` conditional classes. Only two options. Already have Button/icon components. |
| `@radix-ui/react-switch` | Chart toggle | Semantically a switch is for on/off states, not mode selection between two visualization types. |
| `react-select` or `downshift` | Missionary selector dropdown | `@radix-ui/react-select` v2.2.6 already installed, used for every dropdown in the app. |
| `chart.js` or `victory` | Additional chart types | Recharts 3.6.0 already has BarChart, LineChart, PieChart (donut via innerRadius), AreaChart. |
| `framer-motion` | Prayer session transitions | CSS transitions + Tailwind `transition-all` are sufficient for the calm, minimal prayer UI aesthetic. |
| `django-guardian` or `django-rules` | Object-level permissions for supervisor | Queryset filtering in `get_queryset()` is the established pattern (25+ methods). Object-level permission packages add complexity for a problem already solved. |
| `zustand` or `jotai` | Global state for selected missionary | nuqs URL params + React Query cache handle this with existing patterns. Selected missionary ID is URL state, not app state. |
| `nivo` or `tremor` | Progress bar / metric cards | Radix Progress component + Card component already exist and match the design system. Adding a chart library for a progress bar is extreme overkill. |
| New Django role/permission package | Mission Supervisor role | Django's `TextChoices` enum + DRF `BasePermission` subclasses + queryset filtering is the proven pattern used for 4 existing roles. |

---

## Installation

### Backend

```bash
# NO new Python packages needed for v2.2
# Django 4.2.28 handles: model changes, migrations, M2M, queryset filtering, permissions
# DRF handles: serialization, view permissions, API responses
```

### Frontend

```bash
# NO new npm packages needed for v2.2
# All features use already-installed packages:
# - recharts 3.6.0 (bar, line, pie/donut charts)
# - @radix-ui/react-progress 1.1.8 (progress bar)
# - @radix-ui/react-select 2.2.6 (missionary selector)
# - @radix-ui/react-checkbox 1.3.3 (journal checkbox)
# - nuqs 2.8.8 (URL state for viewing_user)
# - lucide-react 0.562.0 (icons for chart toggle)
```

**Zero new dependencies for the entire v2.2 milestone.**

---

## Integration Points

### Role Propagation Path (Supervisor)

Changes flow through these layers -- all existing, just need the new role value added:

```
1. Backend model    apps/users/models.py          Add SUPERVISOR to UserRole TextChoices
2. Backend migration                              makemigrations (CharField choices, M2M table)
3. Backend perms    apps/core/permissions.py       Update/add permission classes
4. Backend views    apps/*/views.py               Add supervisor elif in get_queryset()
5. Backend serial.  apps/users/serializers.py      Add supervised_users to admin serializer
6. API response     /api/users/me/                 Returns role: "supervisor" (auto from choices)
7. Frontend type    frontend/src/api/users.ts      Add "supervisor" to UserRole union
8. Frontend type    frontend/src/api/auth.ts       Add "supervisor" to User.role type
9. Frontend sidebar frontend/src/.../Sidebar.tsx   Update roleHierarchy, add supervisor access
10. Frontend routes                               Update admin/analytics route guards
```

### Dashboard Selector Data Flow

```
Supervisor/Admin clicks missionary selector
  -> nuqs updates URL: ?viewing_user=<uuid>
  -> React Query key includes viewing_user: ['dashboard-summary', { viewing_user: uuid }]
  -> API call: GET /api/dashboard/summary/?user_id=<uuid>
  -> Backend validates: requesting user has permission to view target user
  -> Response: dashboard data scoped to selected missionary
  -> UI renders: selected missionary's dashboard with selector showing their name
```

### Journal Report Data Flow (no changes)

```
Existing endpoint: GET /api/journals/{id}/report/
  -> Returns: journal metadata, summary stats (total contacts, stalled, stage distribution,
              decisions with counts/amounts, goal progress, next steps)
  -> Frontend rebuilds: 4 metric cards, progress bar, bar chart, donut chart
  -> Removes: Pipeline Breakdown chart, extra decision column
  -> Changes: Checkbox click creates stage event directly (no LogEventDialog)
```

---

## Alternatives Considered

| Category | Chosen | Alternative | Why Not |
|----------|--------|-------------|---------|
| Supervisor relationship | M2M on User ('self') | FK on User (supervisor_id) | FK limits to 1 supervisor per missionary. M2M allows multiple supervisors. |
| Supervisor relationship | M2M on User ('self') | Separate SupervisorAssignment model | No metadata needed on the relationship. Django M2M join table is sufficient. |
| Missionary selector state | nuqs URL param | React context/state | URL state is the app convention (filters, date ranges all use nuqs). Makes selection shareable and bookmarkable. |
| Chart toggle UI | Button pair with cn() | @radix-ui/react-toggle-group | Not installed, would add a dependency for a 2-option toggle. Buttons are simpler. |
| Chart toggle UI | Button pair with cn() | @radix-ui/react-tabs | Semantically wrong: tabs switch content panels, toggle switches visualization of same data. |
| Journal progress bar | Radix Progress + composed label | Custom CSS-only progress bar | Radix Progress provides accessibility (role, aria-valuenow, etc.) for free. |
| Journal progress bar | Radix Progress + composed label | Recharts RadialBar/Gauge | Overkill for a linear progress bar. Radix Progress is purpose-built. |
| Permission scoping | Queryset filtering in views | django-guardian per-object permissions | Queryset filtering is the proven pattern across 25+ methods. Object-level permissions add a permissions table and middleware overhead for something already solved. |

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Zero new packages | HIGH | Verified every feature against installed packages and existing code patterns |
| Recharts chart types | HIGH | BarChart, PieChart (donut), LineChart all actively used in production code files |
| Radix Progress | HIGH | Component exists at `components/ui/progress.tsx`, installed at v1.1.8 |
| Supervisor role via M2M | HIGH | Django `ManyToManyField('self')` is documented, queryset scoping proven across 25+ view methods |
| Chart toggle pattern | HIGH | BarChart and LineChart share identical data shape and Recharts API for axes/grid/tooltips |
| Begin Prayer expansion | HIGH | Existing `PrayerFocusMode.tsx` is 243 lines of complete focus mode -- only needs entry point |
| Missionary selector | HIGH | Exact pattern (Radix Select + query param) already used for owner filter on contacts page |

---

## Sources

- Recharts 3.0 migration guide: [GitHub Wiki](https://github.com/recharts/recharts/wiki/3.0-migration-guide)
- Codebase analysis: `frontend/package.json` (all installed versions), `requirements/base.txt` (Python deps)
- Existing donut chart: `frontend/src/components/dashboard/GivingSummaryCard.tsx` lines 80-94
- Existing bar chart: `frontend/src/components/dashboard/MonthlyGiftsCard.tsx` lines 60-99
- Existing line chart: `frontend/src/pages/admin/analytics/UserDetail.tsx` lines 248-280
- Existing progress component: `frontend/src/components/ui/progress.tsx` (Radix-based)
- Existing chart wrapper: `frontend/src/components/ui/chart.tsx` (shadcn/ui ChartContainer)
- Permission patterns: `apps/core/permissions.py` (6 permission classes)
- Queryset scoping: `apps/contacts/views.py` (10 methods), `apps/journals/views.py` (11 methods)
- Role infrastructure: `apps/users/models.py` (UserRole TextChoices), `apps/users/serializers.py`
- Frontend role types: `frontend/src/api/auth.ts` (User interface), `frontend/src/api/users.ts` (UserRole type)
- Sidebar role gating: `frontend/src/components/layout/Sidebar.tsx` (roleHierarchy, requiredRole)
- Feature specs: `prompts/mission_supervisor.md`, `prompts/journal_report.md`, `prompts/dashboard_modification.md`, `prompts/prayer_intentions.md`
- Prayer focus mode: `frontend/src/pages/prayer/PrayerFocusMode.tsx` (243 lines, complete)

---
*Stack research for: v2.2 UI Polish, Journal Report Rebuild & Mission Supervisor Role*
*Researched: 2026-02-26*
*Confidence: HIGH -- Zero new dependencies. All features use already-installed packages verified against source code.*
