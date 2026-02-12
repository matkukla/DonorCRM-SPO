# Admin Analytics Dashboard Pitfalls

**Domain:** Adding admin analytics dashboard to existing Django/React CRM
**Researched:** 2026-02-12
**Context:** DonorCRM v1.2 — 10-20 coaches monitoring 200+ missionaries

---

## CRITICAL PITFALLS

### Pitfall 1: Cross-User Aggregation Without Role Filter

**What goes wrong:** Admin analytics endpoint aggregates data across ALL users in the database instead of respecting role-based access.

**Why it happens:** Copy-paste from user-scoped views, forgetting to add role check. Common pattern:
```python
# WRONG - admin sees all data without checking if they should
def admin_analytics(request):
    donations = Donation.objects.all()  # No role check!
```

**Existing vulnerability in codebase:** Edge case audit already identified inconsistent role checks. `admin_summary` uses `is_staff` while other endpoints use `role == 'admin'` (issue 1.5).

**Consequences:**
- Finance users see missionary journal data they shouldn't access
- Read-only users bypass restrictions via analytics endpoints
- GDPR/privacy violation if coaches see each other's donors

**Prevention:**
```python
# CORRECT - consistent role filtering
def admin_analytics(request):
    if request.user.role != 'admin':
        return Response({'error': 'Admin only'}, status=403)
    # Now safe to aggregate across users
    donations = Donation.objects.all()
```

**Detection:**
- API test: Finance user calls `/api/v1/admin/analytics/` → should get 403
- Check all new endpoints have explicit `role == 'admin'` guard (not `is_staff`)

**Phase impact:** Must address in Phase 1 (permissions setup) before any aggregation logic.

---

### Pitfall 2: N+1 Queries on Cross-User Data Loads

**What goes wrong:** Admin dashboard loads 200 missionaries' data. Each missionary triggers 3-7 queries for related stats. Total: 600-1400 queries for a single page load.

**Why it happens:** Existing system already has N+1 issues (Edge case audit issue 1.1: journal grid does 7N queries per contact). Adding cross-user aggregation multiplies this by number of users.

**Example:**
```python
# WRONG - N+1 disaster
missionaries = User.objects.filter(role='missionary')  # 1 query
for m in missionaries:
    total_contacts = m.contacts.count()  # +200 queries
    total_donations = Donation.objects.filter(contact__owner=m).count()  # +200 queries
    active_journals = m.journals.filter(is_active=True).count()  # +200 queries
```

**Consequences:**
- Dashboard timeout (>30s load time with 200 users)
- Database connection pool exhaustion
- Render.com free tier kills request after 30s
- Admin can't actually use the dashboard

**Prevention:**
```python
# CORRECT - single query with annotations
missionaries = User.objects.filter(role='missionary').annotate(
    total_contacts=Count('contacts'),
    total_donations=Count('contacts__donations'),
    active_journals=Count('journals', filter=Q(journals__is_active=True))
)
# Now iterate over results - no additional queries
```

**For complex stats requiring serializer access:**
```python
# Use select_related and prefetch_related
users = User.objects.filter(role='missionary').select_related(
    'profile'
).prefetch_related(
    Prefetch('contacts', queryset=Contact.objects.only('id', 'owner_id')),
    Prefetch('journals', queryset=Journal.objects.filter(is_active=True))
)
```

**Detection:**
- django-debug-toolbar in development shows query count
- Log warning if endpoint executes >50 queries
- Load test: 200 users should complete in <3s

**Phase impact:** Must address in Phase 2 (dashboard backend). Every aggregation endpoint needs query optimization audit.

**Related known issue:** Edge case audit issue 5.2 documents dashboard already makes 10+ redundant queries for single-user view.

---

### Pitfall 3: Permission Bypass via ListAPIView

**What goes wrong:** Admin analytics list view uses `IsAdminOrReadOnly` permission class, but DRF's `ListAPIView` only checks `has_permission()`, not `has_object_permission()`.

**Why it happens:** Existing codebase has this exact bug (Edge case audit issue 2.2/4.1). `IsContactOwnerOrReadAccess` never fires on list views because it only implements `has_object_permission()`.

**Example:**
```python
# WRONG - permission class is ignored!
class MissionaryStatsView(ListAPIView):
    permission_classes = [IsAdminOnly]  # This only has has_object_permission()
    queryset = User.objects.filter(role='missionary')

    # BUG: Any authenticated user can call this
```

**Consequences:**
- Non-admin users can access admin-only aggregation endpoints
- Data leak: missionaries see each other's stats
- Audit log shows "authenticated user" not "admin user"

**Prevention:**
```python
# Option 1: Implement has_permission() in permission class
class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin'

# Option 2: Add explicit check in view
class MissionaryStatsView(ListAPIView):
    def list(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=403)
        return super().list(request, *args, **kwargs)
```

**Detection:**
- Test suite: Read-only user calls admin endpoint → expect 403
- Code review: All `ListAPIView` with admin data must check role in `list()` or permission class
- Grep for `permission_classes` in new views, verify implementation

**Phase impact:** Phase 1 (permissions). Block all analytics work until this pattern is established.

---

### Pitfall 4: Float Arithmetic in Aggregated Money Totals

**What goes wrong:** Dashboard shows "Total given across all missionaries: $49,999.97" when actual total is $50,000.00. Penny discrepancies compound across 200 users.

**Why it happens:** Existing codebase uses float multiplication for `monthly_equivalent` (Edge case audit issue 3.1). Admin dashboard aggregates these floats, amplifying rounding errors.

**Example:**
```python
# WRONG - float arithmetic compounds errors
total = sum(float(p.monthly_equivalent) * 12 for p in all_pledges)
# With 200 missionaries × 50 pledges each, expect multiple penny errors
```

**Consequences:**
- Dashboard "Total Monthly Pledges" doesn't match sum of individual user totals
- Finance team loses trust in analytics
- Debugging nightmare: "Why is the total off by $0.43?"

**Prevention:**
```python
# CORRECT - use Decimal throughout
from decimal import Decimal

# In model property (fix existing code too):
@property
def monthly_equivalent(self):
    multipliers = {'weekly': Decimal('4.33'), 'monthly': Decimal('1'), ...}
    return self.amount * multipliers[self.frequency]

# In aggregation:
from django.db.models import Sum, DecimalField
from django.db.models.functions import Cast

total_monthly = Pledge.objects.filter(
    status='ACTIVE'
).annotate(
    monthly=Cast('amount', DecimalField()) * Case(
        When(frequency='weekly', then=Decimal('4.33')),
        When(frequency='monthly', then=Decimal('1')),
        # ...
    )
).aggregate(total=Sum('monthly'))['total']
```

**Detection:**
- Test: Aggregate 1000 $33.33 weekly pledges → should equal $144,652.00 exactly
- Lint rule: Flag `float()` calls on money fields
- Code review: All money aggregations use Decimal

**Phase impact:** Phase 2 (dashboard backend). Fix existing pledge model first, then build aggregations on corrected base.

**Related known issue:** Edge case audit issue 3.1 documents this in pledge monthly_equivalent.

---

### Pitfall 5: Race Conditions in Stat Updates

**What goes wrong:** Admin dashboard shows "Last updated: 2 minutes ago" but displays stale data because concurrent update_giving_stats() calls overwrote each other.

**Why it happens:** Existing race conditions in codebase (Edge case audit issues 2.1, 3.2). When admin triggers bulk operations (e.g., import 500 donations), stats become inconsistent.

**Example scenario:**
1. Admin imports 500 donations via CSV
2. Each save triggers `update_giving_stats()` signal
3. Multiple signals for same contact run concurrently
4. Each reads current `total_given`, adds new amount, saves
5. Last write wins — intermediate donations lost from total

**Consequences:**
- Dashboard shows "Total Given: $45,000" when actual is $48,000
- Stats differ between "All Missionaries" view and individual user view
- Recalculating stats shows different number (red flag to users)

**Prevention:**
```python
# CORRECT - disable signals during bulk operations
from django.db.models.signals import post_save

def bulk_import_donations(donations_data):
    post_save.disconnect(update_giving_stats_signal, sender=Donation)
    try:
        Donation.objects.bulk_create([...])
        # Update stats once per affected contact
        for contact_id in affected_contacts:
            contact = Contact.objects.select_for_update().get(pk=contact_id)
            contact.update_giving_stats()
    finally:
        post_save.connect(update_giving_stats_signal, sender=Donation)

# In update method, use F() expressions:
def update_giving_stats(self):
    # Atomic increment, no race condition
    Contact.objects.filter(pk=self.pk).update(
        total_given=F('total_given') + new_amount
    )
    self.refresh_from_db()
```

**Detection:**
- Test: Import 100 donations for same contact simultaneously → stats should be exact
- Monitor: Log when `update_giving_stats()` is called >5 times for same contact in 1 second
- Load test: Concurrent admin operations should produce consistent stats

**Phase impact:** Phase 1 (data integrity). Must fix existing race conditions before building dashboard that depends on accurate stats.

**Related known issues:**
- Edge case audit issue 2.1: `update_giving_stats()` race
- Edge case audit issue 3.2: `record_fulfillment()` race

---

## HIGH-PRIORITY PITFALLS

### Pitfall 6: Unbounded Data in Aggregation Endpoints

**What goes wrong:** Admin clicks "View All Missionary Activity" → endpoint returns 50,000 journal events → browser tab freezes → admin force-quits.

**Why it happens:** Existing analytics endpoints already lack pagination (Edge case audit issue 1.4). Cross-user aggregation multiplies data volume.

**Example:**
```python
# WRONG - returns potentially millions of rows
def missionary_activity(request):
    events = JournalStageEvent.objects.filter(
        journal__owner__role='missionary'
    ).select_related('contact', 'journal')
    # No limit! Returns all events ever created.
    return Response(EventSerializer(events, many=True).data)
```

**Consequences:**
- JSON response >10MB
- Serialization takes 30+ seconds
- Browser OOM on large datasets
- Admin dashboard unusable

**Prevention:**
```python
# CORRECT - pagination + date windowing
from rest_framework.pagination import PageNumberPagination

class AdminAnalyticsPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 500

class MissionaryActivityView(ListAPIView):
    pagination_class = AdminAnalyticsPagination

    def get_queryset(self):
        # Default to last 90 days
        days = int(self.request.query_params.get('days', 90))
        start_date = date.today() - timedelta(days=days)

        return JournalStageEvent.objects.filter(
            journal__owner__role='missionary',
            created_at__gte=start_date
        ).select_related('contact', 'journal')[:500]  # Hard limit
```

**Detection:**
- Test: Call endpoint without params → should return ≤500 items
- Monitor: Log warning if serializer processes >1000 objects
- Load test: Response time should be <2s even with max data

**Phase impact:** Phase 2 (dashboard backend). Establish pagination pattern early, apply to all list endpoints.

**Related known issue:** Edge case audit issue 1.4 documents unbounded analytics endpoints.

---

### Pitfall 7: Query Result Timing Inconsistencies

**What goes wrong:** Admin dashboard shows "Total Donations: 1,247" in header but "Recent Donations" widget shows 1,250. User refreshes, numbers change differently.

**Why it happens:** Multiple service functions execute separate queries at slightly different times. Donations created between queries cause inconsistency.

**Example:**
```python
# WRONG - queries run at different times
def get_admin_dashboard(user):
    return {
        'total_donations': Donation.objects.count(),  # Query at T+0ms
        'total_amount': Donation.objects.aggregate(Sum('amount')),  # Query at T+50ms
        'recent_donations': Donation.objects.order_by('-date')[:10],  # Query at T+120ms
    }
# If donation created at T+60ms, count includes it but total_amount doesn't
```

**Consequences:**
- Dashboard appears broken/buggy
- Admins lose trust in data accuracy
- "Why do these numbers not add up?"

**Prevention:**
```python
# Option 1: Single query with subqueries
def get_admin_dashboard(user):
    from django.db.models import Subquery, OuterRef

    # All data from a single point in time
    stats = Donation.objects.aggregate(
        total_count=Count('id'),
        total_amount=Sum('amount'),
    )
    recent = Donation.objects.order_by('-date')[:10]

    return {'count': stats['total_count'], 'amount': stats['total_amount'], 'recent': recent}

# Option 2: Use transaction for consistency
from django.db import transaction

@transaction.atomic
def get_admin_dashboard(user):
    # All queries see same database snapshot
    ...
```

**Detection:**
- Test: Create donation during dashboard load → counts should be consistent
- Monitor: Log if aggregate count != queryset.count() for same data
- Frontend: Display "as of [timestamp]" so users know data is point-in-time

**Phase impact:** Phase 2 (dashboard backend). Design aggregation functions to use shared base queries.

**Related known issue:** Edge case audit issue 5.2 mentions dashboard makes 10+ redundant queries.

---

### Pitfall 8: GET Request with Side Effects (Mark as Read)

**What goes wrong:** Admin opens dashboard → all events marked as "seen" → browser crashes before rendering → events permanently lost as "new" → admin misses critical alerts.

**Why it happens:** Existing dashboard does this (Edge case audit issue 5.1). Cross-user admin dashboard amplifies impact (affects all users' events, not just one).

**Example:**
```python
# WRONG - side effect on GET
class AdminDashboardView(APIView):
    def get(self, request):
        data = get_admin_dashboard(request.user)
        # BUG: Marking as read before user actually sees it
        Event.objects.filter(user__role='missionary', is_new=True).update(is_new=False)
        return Response(data)
```

**Consequences:**
- Browser back button marks events as read
- Prefetch/crawler requests mark events as read
- Admin doesn't realize there are new events because they're auto-marked
- Violates HTTP semantics (GET should be safe/idempotent)

**Prevention:**
```python
# CORRECT - separate POST endpoint for side effects
class AdminDashboardView(APIView):
    def get(self, request):
        data = get_admin_dashboard(request.user)
        # No side effects! Just return data.
        return Response(data)

class MarkEventsSeenView(APIView):
    def post(self, request):
        event_ids = request.data.get('event_ids', [])
        Event.objects.filter(id__in=event_ids, user=request.user).update(is_read=True)
        return Response({'marked': len(event_ids)})
```

**Frontend calls:**
```typescript
// Load dashboard (idempotent)
const { data } = useQuery(['admin-dashboard'], fetchAdminDashboard)

// User explicitly acknowledges events
const markSeen = useMutation(markEventsAsSeen, {
  onSuccess: () => queryClient.invalidateQueries(['admin-dashboard'])
})
```

**Detection:**
- Test: GET /admin/dashboard twice → should return same is_new counts
- Code review: No `.update()`, `.delete()`, or `.create()` in GET handlers
- Browser devtools: Verify no database writes on page refresh

**Phase impact:** Phase 2 (dashboard backend). Establish pattern early: GET = read-only, POST/PATCH = mutations.

**Related known issue:** Edge case audit issue 5.1 documents this in user dashboard.

---

### Pitfall 9: Stale Data Detection Logic Errors

**What goes wrong:** Dashboard "Stalled Contacts" widget shows contacts with no activity in 60 days. But includes contacts created 30 days ago (never had activity vs. activity stopped).

**Why it happens:** Incorrect date comparison logic when detecting staleness across different activity types.

**Example:**
```python
# WRONG - doesn't handle null dates correctly
def get_stalled_contacts(days=60):
    cutoff = date.today() - timedelta(days=days)
    return Contact.objects.filter(
        last_contact_date__lt=cutoff  # BUG: Excludes contacts with NULL last_contact_date
    )
# Misses contacts that NEVER had contact (last_contact_date=NULL)
```

**Consequences:**
- Widget shows incomplete data
- New contacts with no activity don't appear (false negative)
- Admins miss missionaries who need help with new contacts

**Prevention:**
```python
# CORRECT - explicit null handling
def get_stalled_contacts(days=60):
    cutoff = date.today() - timedelta(days=days)

    # Contacts with old activity OR no activity at all
    return Contact.objects.filter(
        Q(last_contact_date__lt=cutoff) | Q(last_contact_date__isnull=True)
    ).filter(
        created_at__lt=cutoff  # But exclude very recently created contacts
    )
```

**Better: Use annotation for clarity**
```python
from django.db.models import Case, When, Value
from django.db.models.functions import Coalesce

def get_stalled_contacts(days=60):
    cutoff = date.today() - timedelta(days=days)

    # Use created_at if last_contact_date is null
    return Contact.objects.annotate(
        effective_last_contact=Coalesce('last_contact_date', 'created_at')
    ).filter(
        effective_last_contact__lt=cutoff
    )
```

**Detection:**
- Test: Create contact 90 days ago with no activity → should appear in stalled list
- Test: Create contact yesterday → should NOT appear in stalled list
- Verify NULL values handled: Contact with last_contact_date=NULL

**Phase impact:** Phase 3 (stalled contact detection). Critical for coach alerts.

---

### Pitfall 10: Inconsistent Aggregation Across Comparison Views

**What goes wrong:** "This Month vs Last Month" comparison shows This Month=$5,000, Last Month=$4,500. User drills into Last Month details, sees $4,800. Numbers don't match.

**Why it happens:** Comparison view uses different filtering logic than detail view. Or timezone inconsistencies (month boundaries at UTC vs local time).

**Example:**
```python
# WRONG - inconsistent month calculation
def get_comparison_data():
    # Uses calendar month
    this_month_start = date.today().replace(day=1)
    donations_this_month = Donation.objects.filter(date__gte=this_month_start)

def get_monthly_detail(year, month):
    # Uses 30-day window (DIFFERENT LOGIC!)
    end = date(year, month, 1)
    start = end - timedelta(days=30)
    donations = Donation.objects.filter(date__gte=start, date__lt=end)
```

**Consequences:**
- Users distrust dashboard
- Finance team finds discrepancies in reports
- Debugging takes hours to find subtle date logic differences

**Prevention:**
```python
# CORRECT - shared utility function
def get_month_range(year, month):
    """Returns (start_date, end_date) for a calendar month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end

def get_comparison_data():
    this_year, this_month = date.today().year, date.today().month
    start, end = get_month_range(this_year, this_month)
    return Donation.objects.filter(date__gte=start, date__lt=end)

def get_monthly_detail(year, month):
    start, end = get_month_range(year, month)
    return Donation.objects.filter(date__gte=start, date__lt=end)
```

**Timezone considerations:**
```python
# Be explicit about timezone
from django.utils import timezone

def get_month_range_aware(year, month):
    # Use server timezone consistently
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), tz)
    # ...
```

**Detection:**
- Test: Comparison total == sum of detail rows
- Test: Month boundary donations counted correctly (e.g., donation at 11:59pm on last day of month)
- Integration test: Frontend displays same numbers as backend aggregates return

**Phase impact:** Phase 4 (comparison views). Establish date utility functions early.

---

## MODERATE PITFALLS

### Pitfall 11: Frontend Chart Rendering with Large Datasets

**What goes wrong:** Admin selects "Show all 200 missionaries" on bar chart → browser freezes for 10 seconds → chart renders but is unreadable (200 bars squished into 800px).

**Why it happens:** Recharts (likely chart library based on existing stack) renders all data points even if not visible. SVG rendering is slow with >100 elements.

**Example:**
```typescript
// WRONG - renders 200 bars
<BarChart data={allMissionaryData}>
  {allMissionaryData.map(m => <Bar key={m.id} dataKey="donations" />)}
</BarChart>
```

**Consequences:**
- Slow, janky UI
- Chart is visually useless (too many bars to read)
- Mobile browsers crash

**Prevention:**
```typescript
// Option 1: Pagination/filtering
const [visibleMissionaries, setVisibleMissionaries] = useState(data.slice(0, 20))

// Option 2: Aggregation (top 10 + "Others")
const topMissionaries = data.sort((a, b) => b.total - a.total).slice(0, 10)
const others = data.slice(10).reduce((sum, m) => sum + m.total, 0)
const chartData = [...topMissionaries, { name: 'Others', total: others }]

// Option 3: Switch to canvas rendering for large datasets
<ResponsiveContainer>
  <BarChart data={chartData}>
    {/* Recharts automatically uses canvas for >50 data points */}
  </BarChart>
</ResponsiveContainer>
```

**For time-series with many points:**
```typescript
// Sample data - show every 10th point for 1000+ point datasets
const sampledData = data.length > 100
  ? data.filter((_, i) => i % Math.ceil(data.length / 100) === 0)
  : data
```

**Detection:**
- Performance test: Render chart with 500 data points → should complete in <1s
- Visual test: Chart should be readable (labels not overlapping)
- Monitor: Log warning if chart receives >100 data points

**Phase impact:** Phase 5 (frontend charts). Design aggregation strategy before implementing charts.

---

### Pitfall 12: Cache Invalidation Timing Issues

**What goes wrong:** Admin imports 100 donations → dashboard still shows old totals → admin refreshes → sees new data → but "Recent Donations" widget still shows old list.

**Why it happens:** React Query cache invalidation happens before backend finishes updating denormalized stats. Or partial invalidation (invalidate totals but not list).

**Example:**
```typescript
// WRONG - invalidates too early
const importDonations = useMutation(importDonationsAPI, {
  onSuccess: () => {
    // BUG: Import is async, stats update happens in background
    queryClient.invalidateQueries(['admin-dashboard'])
    // Dashboard refetches immediately, but stats not updated yet!
  }
})
```

**Consequences:**
- Stale data displayed after mutations
- Admin sees "100 donations imported" toast but count doesn't change
- Must manually refresh to see correct data

**Prevention:**
```typescript
// Option 1: Backend returns updated stats
const importDonations = useMutation(importDonationsAPI, {
  onSuccess: (response) => {
    // Backend includes updated stats in response
    queryClient.setQueryData(['admin-dashboard'], response.updated_stats)
  }
})

// Option 2: Invalidate with refetch delay
const importDonations = useMutation(importDonationsAPI, {
  onSuccess: async () => {
    // Wait for backend to finish stat updates (if import is sync)
    await queryClient.invalidateQueries(['admin-dashboard'])
  }
})

// Option 3: Optimistic update with rollback
const importDonations = useMutation(importDonationsAPI, {
  onMutate: async (newData) => {
    await queryClient.cancelQueries(['admin-dashboard'])
    const previous = queryClient.getQueryData(['admin-dashboard'])

    // Optimistically update
    queryClient.setQueryData(['admin-dashboard'], old => ({
      ...old,
      total_donations: old.total_donations + newData.length
    }))

    return { previous }
  },
  onError: (err, newData, context) => {
    // Rollback on error
    queryClient.setQueryData(['admin-dashboard'], context.previous)
  },
  onSettled: () => {
    queryClient.invalidateQueries(['admin-dashboard'])
  }
})
```

**For granular invalidation:**
```typescript
// Invalidate specific related queries
queryClient.invalidateQueries(['admin-dashboard'])
queryClient.invalidateQueries(['missionary-stats'])
queryClient.invalidateQueries(['donation-list'])
// All keys that could be affected by import
```

**Detection:**
- Test: Import donation → dashboard shows updated count within 2 seconds
- Test: Create mutation → dependent queries refetch
- Monitor: Log if user sees stale data (check last_updated timestamp)

**Phase impact:** Phase 5 (frontend data flow). Establish cache invalidation patterns early.

---

### Pitfall 13: Slide-In Panel State Conflicts

**What goes wrong:** Admin clicks "View Missionary Details" → slide-in opens → admin clicks another missionary → first panel still open but data changes → panel shows mixed data from both missionaries.

**Why it happens:** Slide-in panel state (open/closed) stored separately from data (which missionary). Race condition when clicking quickly.

**Example:**
```typescript
// WRONG - state and data out of sync
const [isPanelOpen, setIsPanelOpen] = useState(false)
const [selectedMissionaryId, setSelectedMissionaryId] = useState(null)
const { data } = useQuery(['missionary', selectedMissionaryId], fetchMissionary)

function openPanel(missionaryId) {
  setIsPanelOpen(true)
  setSelectedMissionaryId(missionaryId)  // Race: data fetch happens before panel opens
}
```

**Consequences:**
- Panel flashes old data before showing new data
- User sees wrong missionary's info briefly
- Confusing UX, looks buggy

**Prevention:**
```typescript
// Option 1: Zustand store (atomic state updates)
import create from 'zustand'

const usePanelStore = create((set) => ({
  selectedMissionaryId: null,
  openPanel: (missionaryId) => set({ selectedMissionaryId: missionaryId }),
  closePanel: () => set({ selectedMissionaryId: null })
}))

function MissionaryPanel() {
  const selectedId = usePanelStore(state => state.selectedMissionaryId)
  const closePanel = usePanelStore(state => state.closePanel)
  const { data } = useQuery(
    ['missionary', selectedId],
    () => fetchMissionary(selectedId),
    { enabled: !!selectedId }
  )

  return (
    <Sheet open={!!selectedId} onOpenChange={(open) => !open && closePanel()}>
      {data && <MissionaryDetails data={data} />}
    </Sheet>
  )
}

// Option 2: Derive open state from data presence
const [selectedMissionaryId, setSelectedMissionaryId] = useState(null)
const isOpen = !!selectedMissionaryId

function openPanel(id) {
  setSelectedMissionaryId(id)  // Single source of truth
}

function closePanel() {
  setSelectedMissionaryId(null)
}
```

**For loading states:**
```typescript
const { data, isLoading } = useQuery(['missionary', selectedId], ...)

<Sheet open={!!selectedId}>
  {isLoading ? <Spinner /> : <MissionaryDetails data={data} />}
</Sheet>
```

**Detection:**
- Test: Rapidly click 5 different missionaries → panel should show correct data each time
- Test: Click missionary A, immediately click missionary B → should never see A's data
- Visual regression test: Panel doesn't flicker

**Phase impact:** Phase 6 (slide-in panels). Establish state management pattern early.

---

### Pitfall 14: Heatmap Calendar Performance Degradation

**What goes wrong:** Admin loads "Donation Activity Heatmap" for past year. 200 missionaries × 365 days = 73,000 cells. Browser freezes, eventually renders but scrolling is janky.

**Why it happens:** SVG-based calendar heatmaps render every cell as a separate DOM element. Even if most cells are empty.

**Example:**
```typescript
// WRONG - renders 73,000 SVG rect elements
<CalendarHeatmap
  startDate={new Date('2025-01-01')}
  endDate={new Date('2025-12-31')}
  values={allDonationData}  // 73,000 entries
/>
```

**Consequences:**
- Slow initial render (5-10 seconds)
- Laggy scrolling
- High memory usage
- Mobile devices crash

**Prevention:**
```typescript
// Option 1: Aggregate by week instead of day (52 weeks vs 365 days)
const weeklyData = aggregateByWeek(allDonationData)
<CalendarHeatmap values={weeklyData} />

// Option 2: Virtualization (only render visible portion)
import { FixedSizeGrid } from 'react-window'

// Option 3: Canvas-based rendering
<HeatmapCanvas
  data={allDonationData}
  renderMode="canvas"  // Much faster for large datasets
/>

// Option 4: Progressive loading
const [visibleMonths, setVisibleMonths] = useState(3)
<CalendarHeatmap
  values={allDonationData.slice(0, visibleMonths * 30)}
/>
<button onClick={() => setVisibleMonths(m => m + 3)}>Load More</button>
```

**For per-user heatmaps:**
```typescript
// Show selected missionary's heatmap only (365 cells, manageable)
const [selectedMissionary, setSelectedMissionary] = useState(null)
const heatmapData = donationData.filter(d => d.missionary_id === selectedMissionary)
```

**Detection:**
- Performance test: Render 10,000 cell heatmap → should complete in <2s
- Lighthouse score: FCP should be <1.5s
- Monitor: Log warning if heatmap receives >1000 data points

**Phase impact:** Phase 7 (heatmap visualizations). Research canvas-based libraries before implementation.

---

### Pitfall 15: Double-Submit on Bulk Operations

**What goes wrong:** Admin clicks "Recalculate All Stats" button. Nothing happens for 3 seconds (slow network). Admin clicks again. Two requests fire. Stats calculated twice, possibly corrupted.

**Why it happens:** Existing codebase has double-submit issues on forms (Edge case audit issue 7.4). Bulk admin operations are even more tempting to double-click.

**Example:**
```typescript
// WRONG - no pending state
function RecalculateButton() {
  const recalculate = useMutation(recalculateStatsAPI)

  return (
    <button onClick={recalculate.mutate}>
      Recalculate All Stats
    </button>
  )
}
```

**Consequences:**
- Duplicate operations (waste server resources)
- Race conditions (two recalculations overwrite each other)
- User confusion (why did it take so long?)

**Prevention:**
```typescript
// CORRECT - disable during pending
function RecalculateButton() {
  const recalculate = useMutation(recalculateStatsAPI, {
    onSuccess: () => {
      toast.success('Stats recalculated successfully')
    },
    onError: (error) => {
      toast.error(`Failed: ${error.message}`)
    }
  })

  return (
    <button
      onClick={() => recalculate.mutate()}
      disabled={recalculate.isPending}
    >
      {recalculate.isPending ? (
        <>
          <Spinner className="mr-2" />
          Recalculating...
        </>
      ) : (
        'Recalculate All Stats'
      )}
    </button>
  )
}
```

**For long-running operations:**
```typescript
// Show progress + confirm before destructive actions
function RecalculateButton() {
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const recalculate = useMutation(recalculateStatsAPI)

  return (
    <>
      <button onClick={() => setIsConfirmOpen(true)}>
        Recalculate All Stats
      </button>

      <Dialog open={isConfirmOpen}>
        <DialogContent>
          <DialogTitle>Recalculate all missionary stats?</DialogTitle>
          <DialogDescription>
            This will recalculate giving stats for 200+ missionaries.
            It may take 30-60 seconds.
          </DialogDescription>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                recalculate.mutate()
                setIsConfirmOpen(false)
              }}
              disabled={recalculate.isPending}
            >
              {recalculate.isPending ? 'Recalculating...' : 'Confirm'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

**Detection:**
- Test: Simulate slow network (500ms delay), double-click button → only 1 request fires
- Code review: All mutation buttons check `isPending`
- E2E test: Bulk operations complete successfully without duplicate calls

**Phase impact:** Phase 8 (bulk operations UI). Apply to all admin action buttons.

**Related known issue:** Edge case audit issue 7.4 documents double-submit on forms.

---

## MINOR PITFALLS

### Pitfall 16: Missing Loading States on Aggregations

**What goes wrong:** Admin opens dashboard → sees empty state for 2 seconds → data pops in → layout shifts → annoying UX.

**Why it happens:** Aggregation queries are slow (200ms-2s for cross-user data). No loading skeleton.

**Prevention:**
```typescript
function AdminDashboard() {
  const { data, isLoading } = useQuery(['admin-dashboard'], fetchDashboard)

  if (isLoading) {
    return <DashboardSkeleton />  // Skeleton matching final layout
  }

  return <DashboardContent data={data} />
}

// Skeleton preserves layout
function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-3 gap-4">
      <Skeleton className="h-32" />  // Stat card size
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
      <Skeleton className="h-64" />  // Chart size
    </div>
  )
}
```

**Detection:**
- Visual test: Loading state matches final layout (no layout shift)
- Lighthouse: Cumulative Layout Shift score <0.1

**Phase impact:** Phase 5 (frontend). Include in component design.

---

### Pitfall 17: Timezone Inconsistencies in Date Aggregations

**What goes wrong:** Backend aggregates donations by day using UTC. Frontend displays dates in user's local timezone (EST). Donation at 11pm EST on Dec 31 shows as Jan 1 in chart.

**Why it happens:** Django uses UTC by default. Frontend uses browser timezone. No explicit timezone handling.

**Prevention:**
```python
# Backend: Be explicit about timezone
from django.utils import timezone

def get_daily_totals():
    # Use user's timezone for grouping
    user_tz = timezone.get_current_timezone()
    return Donation.objects.annotate(
        day=TruncDate('created_at', tzinfo=user_tz)
    ).values('day').annotate(total=Sum('amount'))
```

```typescript
// Frontend: Display dates consistently
import { format, parseISO } from 'date-fns'

function DonationChart({ data }) {
  return data.map(item => ({
    date: format(parseISO(item.date), 'MMM d, yyyy'),
    total: item.total
  }))
}
```

**Detection:**
- Test: Create donation at 11:59pm local time → should appear in correct day
- Test: User in different timezone sees same daily totals (grouped correctly)

**Phase impact:** Phase 4 (date-based aggregations).

---

### Pitfall 18: Overly Aggressive Cache TTL

**What goes wrong:** Admin dashboard cached for 5 minutes. Admin imports 100 donations, dashboard still shows old data for 4 more minutes.

**Why it happens:** Set cache TTL too high to reduce server load, but breaks real-time feel.

**Prevention:**
```typescript
// Shorter TTL for dashboards, longer for static data
const { data } = useQuery(
  ['admin-dashboard'],
  fetchDashboard,
  {
    staleTime: 30000,  // 30 seconds (not 5 minutes)
    cacheTime: 300000, // Keep in cache for 5 min but mark stale after 30s
  }
)

// Invalidate on mutations
const importDonations = useMutation(importAPI, {
  onSuccess: () => {
    queryClient.invalidateQueries(['admin-dashboard'])
  }
})
```

**Detection:**
- Test: Mutation → dashboard shows new data within 2 seconds
- Monitor: Track cache hit rate (should be 60-80%, not 95%+)

**Phase impact:** Phase 5 (frontend caching strategy).

---

### Pitfall 19: Memory Leaks in Chart Components

**What goes wrong:** Admin navigates between dashboard tabs. After 10 tab switches, browser memory usage climbs from 200MB → 1.5GB → tab crashes.

**Why it happens:** Chart libraries (especially D3-based) don't cleanup event listeners or DOM elements when component unmounts.

**Prevention:**
```typescript
import { useEffect, useRef } from 'react'

function DonationChart({ data }) {
  const chartRef = useRef(null)

  useEffect(() => {
    const chart = createChart(chartRef.current, data)

    // Cleanup on unmount
    return () => {
      chart.destroy()  // Remove event listeners, clear DOM
    }
  }, [data])

  return <div ref={chartRef} />
}
```

**For Recharts (React-based):**
- Usually handles cleanup automatically
- But watch for custom tooltips or event handlers

**Detection:**
- Chrome DevTools Memory Profiler: Take heap snapshot, navigate tabs 10x, take another snapshot → should not grow significantly
- Monitor: Track component mount/unmount to verify cleanup

**Phase impact:** Phase 5 (chart implementation).

---

### Pitfall 20: No Error Boundaries on Dashboard Widgets

**What goes wrong:** One widget throws error (e.g., division by zero on percentage calculation). Entire dashboard crashes to white screen.

**Why it happens:** No error boundary wrapping dashboard sections.

**Prevention:**
```typescript
function AdminDashboard() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <ErrorBoundary fallback={<WidgetError />}>
        <MissionaryStatsWidget />
      </ErrorBoundary>

      <ErrorBoundary fallback={<WidgetError />}>
        <DonationChartWidget />
      </ErrorBoundary>
    </div>
  )
}

function WidgetError() {
  return (
    <div className="border border-red-200 bg-red-50 p-4 rounded">
      <p className="text-red-800 font-semibold">Widget failed to load</p>
      <button onClick={() => window.location.reload()}>Refresh page</button>
    </div>
  )
}
```

**Detection:**
- Test: Inject error in widget → rest of dashboard should stay functional
- Sentry error tracking shows isolated widget errors, not full page crashes

**Phase impact:** Phase 5 (dashboard layout).

**Related known issue:** Edge case audit issue 7.3 documents missing error boundary.

---

## PHASE-SPECIFIC WARNINGS

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|----------------|------------|
| Phase 1 | Permission setup | ListAPIView bypass (Pitfall 3) | Implement has_permission() in all permission classes |
| Phase 1 | Permission setup | Inconsistent role checks (Pitfall 1) | Standardize on role=='admin', not is_staff |
| Phase 1 | Data integrity | Race conditions in stats (Pitfall 5) | Fix existing race conditions before building dashboard |
| Phase 2 | Aggregation queries | N+1 queries (Pitfall 2) | Annotate/aggregate in SQL, not Python loops |
| Phase 2 | Aggregation queries | Unbounded results (Pitfall 6) | Default date windowing + pagination |
| Phase 2 | Aggregation queries | Float arithmetic (Pitfall 4) | Use Decimal throughout |
| Phase 2 | Aggregation queries | Timing inconsistencies (Pitfall 7) | Shared base queries or transaction |
| Phase 3 | Stalled contacts | Null date handling (Pitfall 9) | Coalesce null dates with created_at |
| Phase 4 | Comparison views | Inconsistent date logic (Pitfall 10) | Shared date range utilities |
| Phase 4 | Date aggregations | Timezone issues (Pitfall 17) | Explicit timezone in TruncDate |
| Phase 5 | Frontend charts | Large dataset rendering (Pitfall 11) | Canvas rendering + data sampling |
| Phase 5 | Frontend caching | Cache invalidation timing (Pitfall 12) | Optimistic updates or backend returns new stats |
| Phase 5 | Frontend caching | Stale data from high TTL (Pitfall 18) | 30s staleTime, invalidate on mutations |
| Phase 6 | Slide-in panels | State conflicts (Pitfall 13) | Zustand store or derive open from data |
| Phase 6 | Side effects | GET with mutations (Pitfall 8) | Separate POST endpoint for mark-as-read |
| Phase 7 | Heatmaps | Calendar rendering (Pitfall 14) | Canvas mode or weekly aggregation |
| Phase 8 | Bulk operations | Double-submit (Pitfall 15) | Disable button during isPending |
| All phases | Error handling | Missing error boundaries (Pitfall 20) | Wrap widgets in ErrorBoundary |
| All phases | UX | Missing loading states (Pitfall 16) | Skeleton screens matching layout |

---

## INTEGRATION PITFALLS WITH EXISTING SYSTEM

### Known Issue Amplification

Adding cross-user analytics **amplifies** several existing bugs documented in edge case audit:

| Existing Issue | Current Impact | Dashboard Impact |
|----------------|----------------|------------------|
| Journal N+1 (1.1) | 351 queries for 50 contacts | 7000+ queries for 200 missionaries |
| ListAPIView permission bypass (2.2) | One user sees another's data | Admin sees all users' data without check |
| update_giving_stats race (2.1) | Incorrect totals for one contact | Corrupted aggregates across all users |
| record_fulfillment race (3.2) | One pledge's total wrong | All pledges' totals potentially wrong |
| Float money arithmetic (3.1) | Penny errors in one user's view | Compounding errors in cross-user totals |
| Dashboard redundant queries (5.2) | 10+ queries for single user | 2000+ queries for 200 users |
| is_staff vs role inconsistency (1.5) | Admin access confusion | Cross-user data leak |
| GET side effects (5.1) | User's events marked read prematurely | All users' events marked read |

**Critical path:** Fix issues 2.2, 1.5, 2.1, 3.2 BEFORE building cross-user aggregation. Otherwise, security and data integrity problems will be catastrophic at scale.

---

## RESEARCH SOURCES

### Django Performance & Query Optimization
- [Django QuerySet Optimization: Stop Strangling Your API Performance](https://medium.com/@sizanmahmud08/django-queryset-optimization-stop-stranglingyour-api-performance-6bc368d72512)
- [Django ORM select_related and prefetch_related](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)
- [Django N+1 Queries Problem](https://www.scoutapm.com/blog/django-and-the-n1-queries-problem)
- [Django Aggregation Documentation](https://docs.djangoproject.com/en/6.0/topics/db/aggregation/)
- [Django ORM Aggregations Beyond Count() and Sum()](https://medium.com/@priyansu011/django-orm-aggregations-and-annotations-going-beyond-count-and-sum-3016873a3235)

### Django Permissions & Security
- [Django Role-Based Access Control (RBAC)](https://www.permit.io/blog/how-to-implement-role-based-access-control-rbac-into-a-django-application)
- [Django Security Releases 2026](https://www.djangoproject.com/weblog/2026/feb/03/security-releases/)
- [Django Permissions Guide](https://testdriven.io/blog/django-permissions/)
- [Django REST Framework Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [Managing Users in Django Admin](https://realpython.com/manage-users-in-django-admin/)

### React Query & Cache Management
- [React Query Cache Invalidation](https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation)
- [Why Your UI Won't Update: Stale Data in React](https://www.freecodecamp.org/news/why-your-ui-wont-update-debugging-stale-data-and-caching-in-react-apps/)
- [React Query Cache Invalidation Guide](https://medium.com/@kennediowusu/react-query-cache-invalidation-why-your-mutations-work-but-your-ui-doesnt-update-a1ad23bc7ef1)
- [Managing Query Keys for Cache Invalidation](https://www.wisp.blog/blog/managing-query-keys-for-cache-invalidation-in-react-query)

### React Performance & Data Fetching
- [Performance & Request Waterfalls in TanStack Query](https://tanstack.com/query/v5/docs/react/guides/request-waterfalls)
- [Fetch Waterfall in React](https://blog.sentry.io/fetch-waterfall-in-react/)
- [Preventing Waterfall Effect in Data Retrieval](https://rishibakshi.hashnode.dev/how-to-prevent-the-waterfall-effect-in-data-fetching)

### Chart Libraries & Visualization
- [Recharts vs Chart.js Performance for Big Data](https://www.oreateai.com/blog/recharts-vs-chartjs-navigating-the-performance-maze-for-big-data-visualizations/4aff3db4085050dc635fd25267846922)
- [Best React Chart Libraries 2025](https://blog.logrocket.com/best-react-chart-libraries-2025/)
- [Recharts Performance Guide](https://recharts.github.io/en-US/guide/performance/)
- [Best Heatmap Libraries for React](https://blog.logrocket.com/best-heatmap-libraries-react/)
- [React HeatMap Large Data Performance](https://ej2.syncfusion.com/react/demos/heatmap-chart/large-data/)
- [How To Render Large Datasets In React](https://www.syncfusion.com/blogs/post/render-large-datasets-in-react)

### State Management
- [State Management in 2026: Zustand, Signals, Redux](https://veduis.com/blog/state-management-comparing-zustand-signals-redux/)
- [React State Management Tools 2026](https://www.syncfusion.com/blogs/post/react-state-management-libraries)
- [React State Management 2025: What You Actually Need](https://www.developerway.com/posts/react-state-management-2025)

### Stale Data Detection
- [Stale Data: How to Identify and Mitigate Impact](https://www.acceldata.io/blog/how-to-identify-and-eliminate-stale-data-to-optimize-business-decisions)
- [Stale Data: Prevention and Data Decay](https://www.quadratichq.com/blog/stale-data-how-to-identify-prevent-and-overcome-data-decay)

---

## CONFIDENCE ASSESSMENT

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Django query optimization | HIGH | Official docs + edge case audit analysis + existing codebase patterns |
| Permission pitfalls | HIGH | DRF official docs + security releases + existing codebase issues |
| React Query cache | MEDIUM | TanStack official docs + community articles, but no 2026-specific content |
| Chart performance | MEDIUM | Multiple library comparisons + performance guides, general patterns apply |
| State management | MEDIUM | 2026 ecosystem articles + official Zustand docs |
| Stale data detection | LOW | General articles, not specific to CRM analytics dashboards |

**Overall confidence:** MEDIUM-HIGH

Research based on:
- Existing DonorCRM edge case audit (known issues documented)
- Official Django/DRF/TanStack documentation
- 2026 ecosystem articles where available
- General patterns verified across multiple sources

**Gaps:**
- Limited 2026-specific content for React dashboard patterns (most sources are 2025)
- No domain-specific research on CRM admin dashboards (general dashboard advice applied)
- Stale data detection strategies are generic, not CRM-specific

---

*Research complete. Ready for roadmap creation.*
