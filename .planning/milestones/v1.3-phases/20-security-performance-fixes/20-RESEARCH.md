# Phase 20: Security & Performance Fixes - Research

**Researched:** 2026-02-17
**Domain:** Django REST Framework security (queryset scoping, file upload limits), query optimization (N+1), Decimal arithmetic, React routing guards, REST API side effects
**Confidence:** HIGH

## Summary

This phase fixes 7 known bugs documented in EDGE_CASE_AUDIT.md. All issues have been precisely located in the codebase with clear root causes and well-defined fixes. There are no library choices to make and no new dependencies to install -- every fix uses existing Django, DRF, and React Router patterns already established in the project.

The fixes divide into three categories: (1) **Security** -- queryset scoping for non-admin users and cross-user contact validation; (2) **Performance** -- N+1 query elimination in the journal grid serializer and Decimal arithmetic for pledge calculations; (3) **UX/Correctness** -- file size limits, frontend route guards, and eliminating a GET side effect on the dashboard.

**Primary recommendation:** Fix security issues first (QAL-01, QAL-02), then performance (QAL-05, QAL-07), then UX (QAL-06, QAL-08, QAL-09). Each fix is independent and can be verified in isolation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Permission scoping (QAL-01, QAL-02):** Silent filter approach -- non-admin users' querysets are scoped to their own data automatically, no 403 errors, no information leakage. Admin users continue to see all data across all missionaries (unscoped querysets).
- **Stage event cross-user access (QAL-02):** Claude's discretion on whether to return validation error or silent "not found" (see Discretion section below).
- **File upload limits (QAL-06):** Max 10 MB. Both client-side (instant feedback) and server-side (safety net). Rejection UX: toast notification "File too large (max 10 MB)". File type restriction: size only for now.
- **Route guards (QAL-08):** Admin-only pages: Analytics dashboard AND Import Center. Non-admin behavior: redirect to home page (not permission denied page). Admin nav items: hidden entirely from sidebar. Direct URL access: redirect to home WITH brief toast explaining they don't have access.
- **Float arithmetic (QAL-07):** Fix code to use Decimal for pledge monthly_equivalent. Run a data migration to recalculate all existing pledge values (fix + migration).
- **N+1 queries (QAL-05):** Just make it fast with prefetch_related, get under 10 queries. No user-facing loading state changes needed.

### Claude's Discretion
- Stage event cross-user rejection pattern (validation error vs silent not-found)
- Dashboard "seen" marking mechanism (explicit action, separate POST, or auto-after-render)
- Whether unseen events need visual distinction in the dashboard UI
- Technical implementation of all query optimizations
- Exact toast message wording for route guard redirects

### Deferred Ideas (OUT OF SCOPE)
- File type restrictions (deferred to Phase 24-25, Smartsheet import)
</user_constraints>

## Standard Stack

### Core (already in project)
| Library | Purpose | Used For |
|---------|---------|----------|
| Django 4.2 + DRF | Backend framework | All backend fixes |
| `django.db.models.Prefetch` | Query optimization | QAL-05 N+1 fix |
| `decimal.Decimal` | Precise arithmetic | QAL-07 pledge fix |
| React Router v6 | Frontend routing | QAL-08 route guards |
| sonner | Toast notifications | QAL-06, QAL-08 user feedback |
| `@tanstack/react-query` | Data fetching | Dashboard invalidation for QAL-09 |

### Supporting (already in project)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| factory_boy + faker | Test factories | All test files |
| pytest + pytest-django | Test runner | All tests |
| `django.test.utils.override_settings` | Setting overrides in tests | QAL-06 size limit tests |

### No New Dependencies Required
This phase uses only existing project dependencies. No `pip install` or `npm install` needed.

## Architecture Patterns

### Pattern 1: Silent Queryset Scoping (QAL-01)
**What:** Non-admin users' querysets are automatically filtered to their own data. No 403 errors -- they simply see an empty list or a 404 for objects they don't own.
**When to use:** Every `ListAPIView` and `ListCreateAPIView` that accesses user-owned data.

**Current pattern already used correctly in most views:**
```python
# Example from contacts/views.py:55-63 (ALREADY CORRECT)
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        queryset = Contact.objects.all()
    else:
        queryset = Contact.objects.filter(owner=user)
    return queryset
```

**Views that need this pattern added (currently missing owner scoping):**
```python
# contacts/views.py:145-149 - ContactDonationsView
# Currently: Donation.objects.filter(contact_id=contact_id) -- NO OWNER CHECK
# Fix:
def get_queryset(self):
    from apps.donations.models import Donation
    contact_id = self.kwargs.get('pk')
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        return Donation.objects.filter(contact_id=contact_id).order_by('-date')
    return Donation.objects.filter(
        contact_id=contact_id, contact__owner=user
    ).order_by('-date')
```

**Complete list of views needing owner scoping added:**

| View | File:Line | Current Filter | Needed Filter |
|------|-----------|---------------|---------------|
| `ContactDonationsView` | contacts/views.py:145 | `contact_id` only | + `contact__owner=user` |
| `ContactPledgesView` | contacts/views.py:163 | `contact_id` only | + `contact__owner=user` |
| `ContactTasksView` | contacts/views.py:181 | `contact_id` + `owner=user` | Already scoped (OK) |
| `ContactJournalEventsView` | contacts/views.py:299 | `journal_contact__journal__owner=user` | Already scoped for non-admin (OK, but uses `['admin']` not `['admin', 'finance', 'read_only']`) |

**Views already correctly scoped (verified, no changes needed):**
- `ContactListCreateView` (contacts/views.py:55)
- `ContactDetailView` (contacts/views.py:97)
- `ContactSearchView` (contacts/views.py:233)
- `ContactEmailsView` (contacts/views.py:206)
- `ContactJournalsView` (contacts/views.py:262)
- `DonationListCreateView` (donations/views.py:50)
- `DonationDetailView` (donations/views.py:103)
- `PledgeListCreateView` (pledges/views.py:29)
- `PledgeDetailView` (pledges/views.py:61)
- `TaskListCreateView` (tasks/views.py:28)
- `TaskDetailView` (tasks/views.py:60)
- `GroupListCreateView` (groups/views.py:21)
- `GroupDetailView` (groups/views.py:49)
- `JournalListCreateView` (journals/views.py:64)
- `JournalDetailView` (journals/views.py:115)
- `JournalStageEventListCreateView` (journals/views.py:152)
- `JournalContactListCreateView` (journals/views.py:193)
- `DecisionListCreateView` (journals/views.py:271)
- `DecisionDetailView` (journals/views.py:323)
- `DecisionHistoryListView` (journals/views.py:348)
- `NextStepListCreateView` (journals/views.py:384)
- `NextStepDetailView` (journals/views.py:415)
- `EventListView` (events/views.py:25)
- `EventDetailView` (events/views.py:42)
- All dashboard service functions (dashboard/services.py)
- All import views (already admin-only via `IsAdmin` permission)

### Pattern 2: Cross-User Contact Validation (QAL-02)
**What:** When creating a stage event via `contact_id`, validate that the contact belongs to the requesting user.
**Where:** `JournalStageEventSerializer.create()` at journals/serializers.py:220-221

**Current code (VULNERABLE):**
```python
contact = Contact.objects.get(id=contact_id)  # No owner check!
```

**Recommended fix (silent not-found):**
```python
# Use silent "not found" pattern -- consistent with how the rest of
# the app handles objects the user doesn't own (returns 404, not 403)
if user.role == 'admin':
    contact = Contact.objects.get(id=contact_id)
else:
    contact = Contact.objects.get(id=contact_id, owner=user)
```

**Discretion recommendation:** Use `Contact.DoesNotExist` exception (which becomes a 404 or validation error) rather than a custom "not authorized" message. Rationale: (1) consistent with the app's existing pattern (e.g., `ContactThankView`, `PledgePauseView` all use `get(pk=pk, owner=user)` with 404 on DoesNotExist), (2) doesn't leak information about whether the contact exists.

### Pattern 3: Prefetch + Python Aggregation (QAL-05)
**What:** Eliminate N+1 queries in the journal grid by prefetching all stage events and decisions in the view's queryset, then processing in Python in the serializer.
**Where:** `JournalContactListCreateView.get_queryset()` and `JournalContactSerializer.get_stage_events()` / `get_decision()`

**Root cause analysis:**
The current `get_stage_events()` method (journals/serializers.py:101-140) executes per `JournalContact`:
1. One `.values('stage').annotate(...)` query (line 110)
2. Up to 6 `.filter(stage=stage).order_by('-created_at').first()` queries (line 130, one per stage with events)
3. Plus `get_decision()` (line 147) does `obj.decisions.first()` -- another query per row

For 50 contacts: up to 351 queries + 50 decision queries = ~400 queries.

**Fix approach:**
```python
# In JournalContactListCreateView.get_queryset(), add:
from django.db.models import Prefetch
from apps.journals.models import JournalStageEvent, Decision

queryset = JournalContact.objects.select_related(
    'journal', 'contact'
).prefetch_related(
    Prefetch(
        'stage_events',
        queryset=JournalStageEvent.objects.order_by('-created_at'),
        to_attr='prefetched_stage_events'
    ),
    Prefetch(
        'decisions',
        queryset=Decision.objects.all(),
        to_attr='prefetched_decisions'
    )
)

# In get_stage_events(), replace DB queries with Python:
def get_stage_events(self, obj):
    events = getattr(obj, 'prefetched_stage_events', [])
    # Group by stage in Python
    by_stage = {}
    for event in events:
        if event.stage not in by_stage:
            by_stage[event.stage] = []
        by_stage[event.stage].append(event)

    # Build summaries from in-memory data
    summaries = {}
    for stage in PipelineStage.values:
        stage_events = by_stage.get(stage, [])
        if stage_events:
            last = stage_events[0]  # Already ordered by -created_at
            summaries[stage] = {
                'has_events': True,
                'event_count': len(stage_events),
                'last_event_date': last.created_at.isoformat(),
                'last_event_type': last.event_type,
                'last_event_notes': last.notes[:100] if last.notes else None,
            }
        else:
            summaries[stage] = {
                'has_events': False,
                'event_count': 0,
                'last_event_date': None,
                'last_event_type': None,
                'last_event_notes': None,
            }
    return summaries

def get_decision(self, obj):
    decisions = getattr(obj, 'prefetched_decisions', [])
    if decisions:
        decision = decisions[0]
        return {
            'id': str(decision.id),
            'amount': str(decision.amount),
            'cadence': decision.cadence,
            'status': decision.status,
            'monthly_equivalent': str(decision.monthly_equivalent),
        }
    return None
```

**Query count after fix:** 3 queries total (1 for JournalContact with JOINs, 1 for prefetch stage_events, 1 for prefetch decisions). This is well under the 10-query target.

### Pattern 4: Decimal Arithmetic for Money (QAL-07)
**What:** Replace float arithmetic in `Pledge.monthly_equivalent` with Decimal to eliminate floating-point errors.
**Where:** `apps/pledges/models.py:137-146`

**Current code (float arithmetic):**
```python
@property
def monthly_equivalent(self):
    multipliers = {
        PledgeFrequency.MONTHLY: 1,
        PledgeFrequency.QUARTERLY: 1 / 3,        # float division!
        PledgeFrequency.SEMI_ANNUAL: 1 / 6,      # float division!
        PledgeFrequency.ANNUAL: 1 / 12,           # float division!
    }
    return float(self.amount) * multipliers.get(self.frequency, 1)
```

**Fixed code (Decimal arithmetic):**
```python
@property
def monthly_equivalent(self):
    multipliers = {
        PledgeFrequency.MONTHLY: Decimal('1'),
        PledgeFrequency.QUARTERLY: Decimal('1') / Decimal('3'),
        PledgeFrequency.SEMI_ANNUAL: Decimal('1') / Decimal('6'),
        PledgeFrequency.ANNUAL: Decimal('1') / Decimal('12'),
    }
    return round(self.amount * multipliers.get(self.frequency, Decimal('1')), 2)
```

**Callers that also use float and need updating:**
| Location | Current Code | Issue |
|----------|-------------|-------|
| `dashboard/services.py:147` | `float(sum(p.monthly_equivalent for p in active_pledges))` | Converts Decimal result to float |
| `dashboard/services.py:226` | `sum(p.monthly_equivalent * 12 for p in active_pledges)` | After fix, this will use Decimal correctly |
| `pledges/views.py:202` | `total_monthly = sum(p.monthly_equivalent for p in active_pledges)` | Same pattern |

After fixing `monthly_equivalent` to return Decimal, the callers will naturally work with Decimal. The `float()` casts in dashboard/services.py are for JSON serialization and can remain (they convert the final Decimal result to float for the API response, which is fine).

**Data migration:** Required to recalculate all existing pledge values. However, `monthly_equivalent` is a `@property` (computed, not stored), so there is no stored data to migrate. The `fulfillment_percentage` is also a property. The only stored monetary fields (`total_expected`, `total_received`) use the model's `amount` field directly and are not affected by the float arithmetic bug. **Therefore, no data migration is actually needed** -- the fix to the property method is sufficient since the values are computed on read. The user requested "run a data migration to recalculate all existing pledge values" but there are no stored `monthly_equivalent` values to recalculate. The planner should note this and create a no-op migration or skip it.

### Pattern 5: Django `DATA_UPLOAD_MAX_MEMORY_SIZE` (QAL-06)
**What:** Enforce a 10 MB file upload limit at both the Django settings level and application level.
**Where:** `config/settings/base.py` (server-side) and frontend import components (client-side)

**Server-side enforcement:**
```python
# In config/settings/base.py, add:
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
```

Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` applies to the entire request body (default: 2.5 MB). Setting it to 10 MB allows CSV uploads up to that size. When exceeded, Django raises `RequestDataTooBig` which DRF converts to a 400 response.

**Application-level enforcement (additional safety net):**
```python
# In each import view, before file.read():
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
if file.size > MAX_FILE_SIZE:
    return Response(
        {'detail': 'File too large (max 10 MB)'},
        status=status.HTTP_400_BAD_REQUEST
    )
```

**Import views that need the size check:**
1. `ContactImportView` (imports/views.py:62)
2. `DonationImportView` (imports/views.py:142)
3. `FundImportView` (imports/views.py:299)
4. `EntityImportView` (imports/views.py:389)
5. `TransactionImportView` (imports/views.py:483)
6. `PledgeImportView` (imports/views.py:605)

**Client-side enforcement (instant feedback):**
The frontend has two import components:
1. `ImportCard` (components/imports/ImportCard.tsx) -- used in ImportExport page
2. `ImportDialog` (components/imports/ImportDialog.tsx) -- used in ImportCenter (SPO imports)
3. `SPOImportTile` (components/imports/SPOImportTile.tsx) -- used in ImportCenter

All three need a file size check with toast notification:
```typescript
// In file selection/drop handler:
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
if (file.size > MAX_FILE_SIZE) {
  toast.error("File too large (max 10 MB)")
  return
}
```

The project already uses `sonner` for toast (imported in hooks/useJournals.ts and present via `<Toaster />` in App.tsx).

### Pattern 6: Frontend Route Guards with Redirect + Toast (QAL-08)
**What:** Non-admin users who navigate to admin-only pages are redirected to home with a toast message.
**Where:** `ProtectedRoute` component (components/auth/ProtectedRoute.tsx) and `Sidebar` (components/layout/Sidebar.tsx)

**Current behavior:**
- `ProtectedRoute` shows a static "Access Denied" div (no redirect, no toast) -- see ProtectedRoute.tsx:38-48
- `Sidebar` already hides admin nav items using `canAccess()` filter -- see Sidebar.tsx:91-96 and line 181

**What needs to change:**

1. **`ProtectedRoute`** -- change from showing "Access Denied" to redirecting to `/` with a toast:
```typescript
if (userLevel < requiredLevel) {
  // Import at top: import { toast } from "sonner"
  // Use useEffect to show toast once (not on every render)
  toast.info("You don't have access to that page")
  return <Navigate to="/" replace />
}
```

Note: `toast()` inside render will fire on every render. Need to use `useEffect` or `useRef` to fire once. Best approach:
```typescript
const [shouldRedirect, setShouldRedirect] = useState(false)

useEffect(() => {
  if (requiredRole && user) {
    const roleHierarchy = { admin: 4, finance: 3, staff: 2, read_only: 1 }
    if (roleHierarchy[user.role] < roleHierarchy[requiredRole]) {
      toast.info("You don't have access to that page")
      setShouldRedirect(true)
    }
  }
}, [requiredRole, user])

if (shouldRedirect) {
  return <Navigate to="/" replace />
}
```

2. **`Sidebar`** -- already correctly hides admin items via `canAccess()` filter on `bottomNavItems` and `insightsItems`. The analytics dashboard link and import center link are both under `/admin/*` routes which have `requiredRole="admin"`. **No sidebar changes needed** -- it already hides admin items from non-admins.

**Admin-only pages currently in App.tsx (all already have `requiredRole="admin"`):**
- `/admin` -- AdminUsers
- `/admin/imports` -- ImportCenter
- `/admin/analytics/dashboard` -- AdminAnalyticsDashboard
- `/admin/analytics/stalled` -- StalledContacts
- `/admin/analytics/users/:id` -- UserDetail
- `/insights/review-queue` -- ReviewQueue
- `/insights/transactions` -- Transactions

**Per the user decision, admin-only scope for this phase is:** Analytics dashboard AND Import Center. The existing `requiredRole="admin"` already covers all these routes. The only change needed is in `ProtectedRoute` to redirect + toast instead of showing "Access Denied".

### Pattern 7: Separating GET Side Effect (QAL-09)
**What:** The dashboard GET endpoint marks all `is_new=True` events as `is_new=False` before the user reads them. This is a side effect on a GET request.
**Where:** `DashboardView.get()` at dashboard/views.py:35-36

**Current code:**
```python
def get(self, request):
    user = request.user
    data = get_dashboard_summary(user)
    mark_events_as_not_new(user)  # Side effect! Marks events before user sees them
    return Response(data)
```

**The problem:** If the frontend request succeeds but the response rendering fails (network timeout, browser tab closed), events are already marked as "not new" and the user never sees them. Also, any stale-time-based refetch (React Query's `staleTime: 2 * 60 * 1000`) will re-mark events.

**Discretion recommendation: Move to a separate POST endpoint.**

Rationale:
- The dashboard `staleTime` is 2 minutes (useDashboard.ts:8). React Query may re-fetch on window focus or refetch interval, each time marking events as seen.
- A POST endpoint is the REST-correct approach for a state mutation.
- It's a minimal change: add a new endpoint, call it from the frontend after the dashboard data renders.

**Implementation:**
```python
# New endpoint in dashboard/views.py:
class MarkEventsSeenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        mark_events_as_not_new(request.user)
        return Response({'detail': 'Events marked as seen.'})

# Remove mark_events_as_not_new() call from DashboardView.get()
```

```python
# New URL in dashboard/urls.py:
path('mark-seen/', MarkEventsSeenView.as_view(), name='mark-events-seen'),
```

```typescript
// Frontend: call POST after dashboard renders successfully
// In Dashboard.tsx, add useEffect:
useEffect(() => {
  if (data && !isLoading) {
    api.post('/dashboard/mark-seen/')
  }
}, [data, isLoading])
```

**Discretion recommendation on visual indicators:** The existing dashboard already shows a "What Changed" section with event counts and recent events. The `is_new` field currently has no visual distinction in the frontend -- it's only used for the "total_new" count. Adding visual indicators (e.g., a dot badge, bold text) for unseen events would be a nice enhancement but is not required for this bug fix. **Recommendation: skip visual indicators in this phase** -- the core fix is decoupling the marking from the GET. Visual indicators can be added later if the user requests them.

### Anti-Patterns to Avoid
- **Don't add `has_permission()` to `IsContactOwnerOrReadAccess`:** The user decided on silent filtering (queryset scoping), not permission class changes. Adding `has_permission()` that checks URL kwargs would return 403s, violating the "no 403 errors" decision.
- **Don't use `select_for_update()` for the N+1 fix:** This is a read-only optimization. `select_for_update()` is for write contention.
- **Don't create a custom middleware for file size limits:** Django's built-in `DATA_UPLOAD_MAX_MEMORY_SIZE` handles this natively.
- **Don't use `useNavigate()` imperatively in ProtectedRoute for the redirect:** Use `<Navigate>` component (declarative) which is already the pattern used in the existing code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File upload size limits | Custom middleware | Django `DATA_UPLOAD_MAX_MEMORY_SIZE` | Built-in, handles edge cases (multipart, chunked) |
| Query counting for tests | Manual query log parsing | `django.test.utils.assertNumQueries` / `CaptureQueriesContext` | Standard Django test utility |
| Toast notifications | Custom alert component | `sonner` (`toast()`) | Already in project, positioned at bottom-right |
| Role-based redirects | Custom HOC | `ProtectedRoute` + `<Navigate>` | Already exists, just needs redirect logic |

## Common Pitfalls

### Pitfall 1: Forgetting to scope Detail views after fixing List views
**What goes wrong:** Developer fixes `ContactDonationsView.get_queryset()` (list) but forgets that `ContactDetailView` or action views also need scoping.
**Why it happens:** QAL-01 is described as "ListAPIView" issue, so focus stays on list views.
**How to avoid:** The audit (section 4.1 in EDGE_CASE_AUDIT.md) identified the root cause: `IsContactOwnerOrReadAccess` only implements `has_object_permission()` which `ListAPIView` never calls. Detail views DO call `get_object()` which triggers `has_object_permission()`, so they're already protected. Only the List views missing queryset scoping need fixing.
**Warning signs:** Test with User A requesting User B's contact sub-resources via list endpoints.

### Pitfall 2: Using `prefetch_related` with `to_attr` but accessing the default manager
**What goes wrong:** View adds `Prefetch('stage_events', to_attr='prefetched_stage_events')` but serializer still calls `obj.stage_events.values(...)` (the default reverse manager), triggering new queries.
**Why it happens:** `to_attr` creates a Python list attribute, while the default reverse relation is a lazy queryset manager. They coexist.
**How to avoid:** When using `to_attr`, access via `getattr(obj, 'prefetched_stage_events', [])` in the serializer. Never access `obj.stage_events` (the manager) in the same code path.
**Warning signs:** `assertNumQueries` still shows >10 queries after adding prefetch.

### Pitfall 3: Toast firing on every render in ProtectedRoute
**What goes wrong:** Calling `toast()` directly in render body causes it to fire every time React re-renders the component.
**Why it happens:** React re-renders on state changes, and `ProtectedRoute` wraps all routes.
**How to avoid:** Use `useEffect` with proper dependencies to fire the toast once, then immediately redirect. Or use `useRef` to track whether toast has been shown.
**Warning signs:** User sees multiple identical toast notifications when navigating.

### Pitfall 4: Decimal return type breaks JSON serialization
**What goes wrong:** After fixing `monthly_equivalent` to return `Decimal`, callers that build dicts for `Response()` get `TypeError: Object of type Decimal is not JSON serializable`.
**Why it happens:** Python's `json.dumps()` doesn't handle `Decimal` natively. DRF's `JSONRenderer` handles it via `DjangoJSONEncoder`, but manual dict construction (like in `get_late_donations()`) uses `round()` on the result which returns float.
**How to avoid:** Where `monthly_equivalent` values appear in manual dict construction (dashboard/services.py:113), cast to `float()` at the serialization boundary, or use `str()`. The existing code already does `round(p.monthly_equivalent, 2)` which will return Decimal after the fix -- `float()` wrap is needed.
**Warning signs:** 500 errors on dashboard or pledge summary endpoints after deploying the Decimal fix.

### Pitfall 5: DATA_UPLOAD_MAX_MEMORY_SIZE vs FILE_UPLOAD_MAX_MEMORY_SIZE
**What goes wrong:** Setting only `DATA_UPLOAD_MAX_MEMORY_SIZE` but not `FILE_UPLOAD_MAX_MEMORY_SIZE`.
**Why it happens:** Django has two separate settings. `DATA_UPLOAD_MAX_MEMORY_SIZE` limits the entire request body. `FILE_UPLOAD_MAX_MEMORY_SIZE` controls the threshold at which file data spills to disk (default 2.5 MB). For CSV imports that call `file.read()`, the file is always in memory.
**How to avoid:** Set both to 10 MB. Also add explicit `file.size` check in views as an application-level safety net (more descriptive error message than Django's `RequestDataTooBig`).
**Warning signs:** Large file uploads either fail with a generic Django error or silently get written to disk temp files.

### Pitfall 6: Not testing with two different users
**What goes wrong:** All permission scoping tests use a single user and verify they see their own data. The actual bug is that User A can see User B's data.
**Why it happens:** Test setup is faster with one user.
**How to avoid:** Every permission test must create two users (User A and User B), create data for both, then verify User A cannot see User B's data. The existing test fixtures (`authenticated_client`, `admin_client` in conftest.py) make this easy.
**Warning signs:** Tests pass but the security vulnerability remains because the test only checks the positive case.

## Code Examples

### Example 1: Scoping ContactDonationsView queryset
```python
# File: apps/contacts/views.py
# Source: Pattern established in ContactListCreateView (same file, line 55)

class ContactDonationsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from apps.donations.models import Donation
        contact_id = self.kwargs.get('pk')
        user = self.request.user

        if user.role in ['admin', 'finance', 'read_only']:
            return Donation.objects.filter(contact_id=contact_id).order_by('-date')
        return Donation.objects.filter(
            contact_id=contact_id, contact__owner=user
        ).order_by('-date')

    def get_serializer_class(self):
        from apps.donations.serializers import DonationSerializer
        return DonationSerializer
```

### Example 2: Stage event contact_id validation
```python
# File: apps/journals/serializers.py, in JournalStageEventSerializer.create()
# Source: Pattern from ContactThankView (contacts/views.py:124-127)

def create(self, validated_data):
    request = self.context.get('request')
    user = request.user if request else None

    contact_id = validated_data.pop('contact_id', None)

    if not validated_data.get('journal_contact') and contact_id:
        from apps.contacts.models import Contact

        # Scope to user's own contacts (admin can access all)
        if user and user.role == 'admin':
            contact = Contact.objects.get(id=contact_id)
        else:
            contact = Contact.objects.get(id=contact_id, owner=user)
        # ... rest of method unchanged
```

### Example 3: File size validation (server-side)
```python
# File: apps/imports/views.py
# Source: Django docs on file upload handling

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

class ContactImportView(APIView):
    def post(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided.'}, status=400)

        file = request.FILES['file']

        # Size check (before reading into memory)
        if file.size > MAX_UPLOAD_SIZE:
            return Response(
                {'detail': 'File too large (max 10 MB)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file.name.endswith('.csv'):
            return Response({'detail': 'File must be a CSV.'}, status=400)
        # ... rest unchanged
```

### Example 4: File size validation (client-side)
```typescript
// File: frontend/src/components/imports/ImportCard.tsx
// Add to handleDrop and handleFileSelect

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB

const handleDrop = (e: React.DragEvent) => {
  e.preventDefault()
  setIsDragging(false)
  const droppedFile = e.dataTransfer.files[0]
  if (!droppedFile) return
  if (droppedFile.size > MAX_FILE_SIZE) {
    toast.error("File too large (max 10 MB)")
    return
  }
  if (!droppedFile.name.endsWith(".csv")) {
    setError("Please upload a CSV file")
    return
  }
  setFile(droppedFile)
  setResult(null)
  setError(null)
}
```

### Example 5: Asserting query count in tests
```python
# Source: Django test docs
from django.test.utils import CaptureQueriesContext
from django.db import connection

def test_journal_grid_query_count(self):
    # Create 50 journal contacts with stage events
    # ...

    with CaptureQueriesContext(connection) as ctx:
        response = self.client.get(
            f'/api/v1/journals/contacts/?journal_id={journal.id}'
        )

    assert response.status_code == 200
    assert len(ctx) < 10, f"Expected <10 queries, got {len(ctx)}"
```

## Dashboard URLs Reference

For QAL-09, the dashboard URL structure:

```python
# apps/dashboard/urls.py (needs new mark-seen endpoint):
urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('what-changed/', WhatChangedView.as_view(), name='what-changed'),
    path('needs-attention/', NeedsAttentionView.as_view(), name='needs-attention'),
    # ... existing endpoints ...
    path('mark-seen/', MarkEventsSeenView.as_view(), name='mark-events-seen'),  # NEW
]
```

## Open Questions

1. **monthly_equivalent data migration**
   - What we know: `monthly_equivalent` is a `@property` on the Pledge model (computed, not stored in DB). The user requested "run a data migration to recalculate all existing pledge values."
   - What's unclear: Since there's no stored `monthly_equivalent` column, what should the migration recalculate? The `total_expected` and `total_received` fields are stored but computed from `amount` directly, not from `monthly_equivalent`.
   - Recommendation: Create a no-op migration that documents the fix. Or, if the user intended to verify/fix `total_expected` values, scope a separate verification query. The planner should clarify this with the user or note it as "no migration needed since the property is computed on read."

2. **ContactJournalEventsView role scoping inconsistency**
   - What we know: This view (contacts/views.py:309) uses `if user.role not in ['admin']:` -- meaning only admin sees all. Finance and read_only are filtered to their own data.
   - What's unclear: Other contact-adjacent views (ContactDonationsView, ContactPledgesView) scope to `['admin', 'finance', 'read_only']` per the existing contact visibility rules.
   - Recommendation: Make consistent with other contact views. Finance and read_only should see journal events for contacts they can view. But this is a new feature change, not a security fix. Keep current behavior for this phase.

## Sources

### Primary (HIGH confidence)
- Codebase audit: `EDGE_CASE_AUDIT.md` -- comprehensive file-by-file analysis of all 7 issues
- Direct code reading of all affected files (views, serializers, models, settings, frontend components)

### Verification
- Django docs on `DATA_UPLOAD_MAX_MEMORY_SIZE` -- confirmed default is 2.5 MB, setting to 10 MB is straightforward
- Django docs on `Prefetch` objects with `to_attr` -- confirmed this is the standard pattern for eliminating N+1
- `sonner` library -- already used in project (hooks/useJournals.ts, components/ui/sonner.tsx)
- React Router v6 `<Navigate>` component -- already used in project (ProtectedRoute.tsx:29, App.tsx:108)

## Metadata

**Confidence breakdown:**
- QAL-01 (permission scoping): HIGH -- exact files and lines identified, clear fix pattern already used elsewhere in codebase
- QAL-02 (cross-user contact): HIGH -- single line fix, pattern matches existing code
- QAL-05 (N+1 queries): HIGH -- root cause in serializer confirmed, prefetch pattern well-understood, similar pattern already used in ContactJournalsView (contacts/views.py:269-284)
- QAL-06 (file size limits): HIGH -- Django built-in setting, explicit size check is trivial
- QAL-07 (Decimal arithmetic): HIGH -- already correctly implemented in Decision.monthly_equivalent (journals/models.py:281-291), just need to match that pattern
- QAL-08 (route guards): HIGH -- existing ProtectedRoute just needs redirect behavior change
- QAL-09 (dashboard side effect): HIGH -- straightforward endpoint separation

**Research date:** 2026-02-17
**Valid until:** Indefinite (fixes for known bugs, not library version dependent)
