# Architecture Patterns: Admin Analytics Dashboard

**Domain:** Admin Analytics for DonorCRM
**Researched:** 2026-02-12
**Confidence:** HIGH

---

## Recommended Architecture

**Extend existing `insights` app for admin analytics endpoints.**

### Rationale

DonorCRM already has a clear separation of concerns:
- **`dashboard` app** — per-user aggregations (my giving stats, my alerts, my trends)
- **`insights` app** — reports and analytics (donations by month/year, late donations, transactions)
- **`journals` app** — journal CRUD and journal-specific analytics (decision trends, pipeline breakdown, admin_summary)

Admin analytics fits the **`insights`** app pattern: cross-user aggregation for reporting. It already has admin-only endpoints (`ReviewQueueView`, `TransactionsView`) with role-based visibility.

### Alternative Considered: New `admin_analytics` App

**Why not chosen:**
- Adds complexity for 5-7 endpoints
- Duplicates permission patterns already in `insights`
- Creates ambiguity: "Is this insights or admin analytics?"
- Hybrid approach (overview dashboard vs separate pages) from search results suggests dividing by *function* (overview vs drill-down), not by *audience* (admin vs user)

### Pattern Match

The existing codebase already implements this pattern:
- `insights/views.py:ReviewQueueView` — admin-only, cross-user aggregation
- `journals/views.py:JournalAnalyticsViewSet.admin_summary` — admin-only, cross-user aggregation

Admin analytics dashboard extends this pattern with more endpoints and more complex queries.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
├─────────────────────────────────────────────────────────────┤
│  /admin/analytics/dashboard  (Overview page)                │
│  /admin/analytics/stalled    (Stalled contacts page)        │
│  /admin/analytics/users/:id  (User detail page)             │
│                                                              │
│  Components:                                                 │
│  - ConversionFunnelChart (Recharts funnel/bar)              │
│  - TeamActivityTable (React Table)                          │
│  - StalledContactsTable (React Table + pagination)          │
│  - TrendChart (Recharts line)                               │
│  - UserDrilldownPanel (slide-in sidebar)                    │
│  - AlertsPanel (summary cards)                              │
└─────────────────────────────────────────────────────────────┘
                              ↓ HTTP GET
┌─────────────────────────────────────────────────────────────┐
│              Backend API (Django + DRF)                      │
├─────────────────────────────────────────────────────────────┤
│  /api/v1/insights/admin-dashboard/                          │
│    → AdminDashboardView (APIView)                           │
│    → Returns: summary_cards, conversion_funnel,             │
│                team_activity, trend_data, alerts             │
│                                                              │
│  /api/v1/insights/stalled-contacts/                         │
│    → StalledContactsView (APIView)                          │
│    → Returns: paginated contacts with last_activity_date    │
│                                                              │
│  /api/v1/insights/user-performance/<user_id>/               │
│    → UserPerformanceView (APIView)                          │
│    → Returns: per-user metrics, journal_list,               │
│                donation_trend, stage_activity                │
│                                                              │
│  /api/v1/insights/conversion-funnel/                        │
│    → ConversionFunnelView (APIView)                         │
│    → Returns: stage counts with drill-down contact IDs      │
│                                                              │
│  /api/v1/insights/team-activity/                            │
│    → TeamActivityView (APIView)                             │
│    → Returns: recent activity by user (events, stages)      │
│                                                              │
│  Permission: IsAdmin or IsFinanceOrAdmin                    │
│  Query Pattern: Cross-user aggregation with                 │
│                 select_related + prefetch_related +         │
│                 annotate                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓ SQL
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQL Database                            │
├─────────────────────────────────────────────────────────────┤
│  Aggregation Sources:                                        │
│  - JournalStageEvent (stage, created_at)                    │
│  - Decision (amount, cadence, status)                       │
│  - Donation (amount, date, contact, fund)                   │
│  - Pledge (amount, frequency, status)                       │
│  - Contact (owner, last_gift_date, total_given)             │
│  - Task (owner, status, due_date)                           │
│  - Event (user, event_type, created_at)                     │
│  - JournalContact (journal, contact, many-to-many)          │
│  - Journal (owner, name, goal_amount)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### Backend Components

| Component | Responsibility | Location | New/Modified |
|-----------|---------------|----------|--------------|
| `AdminDashboardView` | Aggregate overview metrics across all users | `insights/views.py` | NEW |
| `StalledContactsView` | Detect contacts with 14+ days no activity | `insights/views.py` | NEW |
| `UserPerformanceView` | Per-user performance metrics and trends | `insights/views.py` | NEW |
| `ConversionFunnelView` | Pipeline stage counts for conversion funnel | `insights/views.py` | NEW |
| `TeamActivityView` | Recent activity across all users | `insights/views.py` | NEW |
| `admin_analytics_services.py` | Business logic for metrics calculation | `insights/services.py` | MODIFIED (extend) |
| `IsAdmin` permission | Admin-only access control | `core/permissions.py` | EXISTING |
| `IsFinanceOrAdmin` permission | Finance or admin access | `core/permissions.py` | EXISTING |

### Frontend Components

| Component | Responsibility | Location | New/Modified |
|-----------|---------------|----------|--------------|
| `AdminAnalyticsDashboard.tsx` | Overview page layout with all widgets | `pages/admin/AdminAnalyticsDashboard.tsx` | NEW |
| `StalledContacts.tsx` | Stalled contacts page with table + pagination | `pages/admin/StalledContacts.tsx` | NEW |
| `UserPerformance.tsx` | User detail page with trends and journals | `pages/admin/UserPerformance.tsx` | NEW |
| `ConversionFunnelChart.tsx` | Funnel visualization (Recharts) | `components/analytics/ConversionFunnelChart.tsx` | NEW |
| `TeamActivityTable.tsx` | Activity table (React Table) | `components/analytics/TeamActivityTable.tsx` | NEW |
| `TrendChart.tsx` | Line chart for trends (Recharts) | `components/analytics/TrendChart.tsx` | NEW |
| `UserDrilldownPanel.tsx` | Slide-in sidebar for user quick view | `components/analytics/UserDrilldownPanel.tsx` | NEW |
| `useAdminAnalytics.ts` | React Query hooks for analytics data | `hooks/useAdminAnalytics.ts` | NEW |
| `App.tsx` | Add admin analytics routes | `App.tsx` | MODIFIED |
| `AppLayout.tsx` | Add admin analytics nav item | `components/layout/AppLayout.tsx` | MODIFIED |

---

## Data Flow

### Overview Dashboard Request Flow

```
1. User navigates to /admin/analytics/dashboard
   ↓
2. AdminAnalyticsDashboard.tsx renders
   ↓
3. useAdminDashboard() hook calls GET /api/v1/insights/admin-dashboard/
   ↓
4. AdminDashboardView.get(request)
   ↓
5. Call service functions (from insights/services.py):
   - get_summary_cards(user)
   - get_conversion_funnel(user)
   - get_team_activity(user, limit=10)
   - get_donation_trend(user, months=12)
   - get_alerts(user)
   ↓
6. Each service function:
   - Builds base queryset (all users if admin)
   - Uses annotate() for aggregation
   - Uses select_related/prefetch_related to avoid N+1
   - Returns dict with computed metrics
   ↓
7. View combines all results into single response
   ↓
8. Frontend renders:
   - Summary cards at top
   - Conversion funnel chart (left)
   - Trend chart (right)
   - Team activity table (center)
   - Alerts panel (sidebar)
```

### Stalled Contacts Detection Flow

```
1. User navigates to /admin/analytics/stalled
   ↓
2. StalledContacts.tsx renders with pagination controls
   ↓
3. useStalledContacts(page, limit) hook calls
   GET /api/v1/insights/stalled-contacts/?page=1&limit=50
   ↓
4. StalledContactsView.get(request)
   ↓
5. Call get_stalled_contacts(limit, offset):
   - Subquery: last stage event date per journal_contact
   - Annotate Contact with last_activity_date
   - Filter: last_activity_date < today - 14 days OR NULL
   - Select related: owner, latest stage event
   - Order by: last_activity_date ASC (oldest first)
   - Paginate: offset to offset+limit
   ↓
6. Return paginated result:
   {
     contacts: [...],
     total_count: int,
     page: int,
     page_size: int
   }
   ↓
7. Frontend renders table with:
   - Contact name
   - Owner (missionary)
   - Days since last activity
   - Current pipeline stage
   - Actions (view contact, view journal)
```

### Conversion Funnel Drill-Down Flow

```
1. User clicks on "Decision" stage in funnel chart
   ↓
2. onClick handler captures stage='decision'
   ↓
3. useFunnelDrilldown('decision') hook calls
   GET /api/v1/insights/conversion-funnel/?stage=decision
   ↓
4. ConversionFunnelView.get(request)
   ↓
5. If stage param provided:
   - Query JournalStageEvent.filter(stage=stage)
   - Prefetch related journal_contact, contact, owner
   - Return list of contacts with stage event details
   Otherwise:
   - Return aggregated counts per stage
   ↓
6. Frontend opens UserDrilldownPanel with contact list
```

---

## Integration Points with Existing Components

### 1. Reuse Existing Analytics Endpoints

**Existing:** `journals/views.py:JournalAnalyticsViewSet`
- `decision_trends` — already aggregates Decision objects by month
- `stage_activity` — already aggregates JournalStageEvent by stage and month
- `pipeline_breakdown` — already aggregates current stage counts
- `admin_summary` — already has cross-user aggregation pattern

**Integration:**
- Admin dashboard can call these existing endpoints directly
- Modify to accept optional `user_id` filter for per-user views
- Fix `is_staff` vs `role == 'admin'` inconsistency (Edge Case Audit 1.5)

**Action:** Extend, don't duplicate. Add query params to existing analytics endpoints.

### 2. Reuse Dashboard Service Patterns

**Existing:** `dashboard/services.py`
- `get_giving_summary(user, year)` — aggregates donations per user
- `get_monthly_gifts(user, months)` — monthly donation trends
- `get_support_progress(user)` — pledge aggregation

**Integration:**
- Admin analytics needs similar patterns but across ALL users
- Extract common aggregation logic into shared utility functions
- New pattern: `if user.role == 'admin': qs = Model.objects.all() else: qs = Model.objects.filter(owner=user)`

**Action:** Add `scope_queryset_by_role(qs, user, owner_field='owner')` utility to `insights/services.py`.

### 3. Extend Permission Classes

**Existing:** `core/permissions.py`
- `IsAdmin` — already exists
- `IsFinanceOrAdmin` — already exists
- Pattern: check `request.user.role == 'admin'`

**Integration:**
- Use `IsAdmin` for admin-only endpoints (stalled contacts, user performance)
- Use `IsFinanceOrAdmin` for read-only analytics (conversion funnel, trends)

**Action:** No new permission classes needed. Use existing.

### 4. Extend Insights App URL Structure

**Existing:** `insights/urls.py`
```python
urlpatterns = [
    path('donations-by-month/', ...),
    path('donations-by-year/', ...),
    path('review-queue/', ...),  # admin-only
    path('transactions/', ...),  # admin/finance-only
]
```

**Integration:**
- Add new admin analytics endpoints to same namespace
- Consistent naming: `admin-dashboard`, `stalled-contacts`, `user-performance`

**Action:** Extend `insights/urls.py` with new paths.

### 5. Frontend Routing

**Existing:** `App.tsx`
```tsx
<Route path="/insights/review-queue" element={<ProtectedPage requiredRole="admin">...} />
<Route path="/insights/transactions" element={<ProtectedPage requiredRole="admin">...} />
<Route path="/admin/users" element={<ProtectedPage requiredRole="admin">...} />
<Route path="/admin/imports" element={<ProtectedPage requiredRole="admin">...} />
```

**Integration:**
- Admin analytics uses `/admin/analytics/*` route prefix
- Matches existing admin pages pattern (`/admin/users`, `/admin/imports`)
- Keeps insights for per-user reports, admin for cross-user views

**Action:** Add admin analytics routes under `/admin/analytics/`.

### 6. Navigation Structure

**Existing:** `AppLayout.tsx` has nav items for:
- Dashboard (per-user)
- Contacts
- Donations
- Pledges
- Tasks
- Groups
- Journals
- Insights (reports)
- Admin (users, imports)

**Integration:**
- Add "Analytics" submenu under Admin nav section
- Structure:
  ```
  Admin
  ├─ Users
  ├─ Import Center
  └─ Analytics (NEW)
      ├─ Dashboard
      ├─ Stalled Contacts
      └─ User Performance
  ```

**Action:** Modify `AppLayout.tsx` to add Analytics submenu under Admin.

### 7. Reuse Chart Components

**Existing:** Recharts already used in:
- `insights/DonationsByMonthYear.tsx` — BarChart
- `dashboard/Dashboard.tsx` — Line charts for trends

**Integration:**
- ConversionFunnelChart: Use Recharts BarChart (horizontal bars)
- TrendChart: Reuse LineChart pattern from dashboard
- TeamActivityTable: Use existing React Table patterns from contact/donation lists

**Action:** Follow existing Recharts patterns. No new chart library needed.

---

## New Components Needed

### Backend Services (`insights/services.py`)

```python
def get_admin_dashboard_summary(user):
    """
    Aggregate overview metrics for admin dashboard.
    Returns summary cards, conversion funnel, team activity, trends, alerts.
    """
    if user.role not in ['admin', 'finance']:
        raise PermissionDenied

    return {
        'summary_cards': _get_summary_cards(),
        'conversion_funnel': _get_conversion_funnel(),
        'team_activity': _get_team_activity(limit=10),
        'donation_trend': _get_donation_trend(months=12),
        'alerts': _get_alerts()
    }

def get_stalled_contacts(limit=50, offset=0):
    """
    Detect contacts with 14+ days no activity.
    Activity = JournalStageEvent for contact in any journal.
    """
    # Subquery: latest stage event per contact
    latest_event = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    # Annotate contacts with last activity date
    stalled = Contact.objects.annotate(
        last_activity_date=Subquery(latest_event)
    ).filter(
        Q(last_activity_date__lt=date.today() - timedelta(days=14)) |
        Q(last_activity_date__isnull=True)
    ).select_related('owner').order_by('last_activity_date')

    total = stalled.count()
    contacts = stalled[offset:offset+limit]

    return {
        'contacts': contacts,
        'total_count': total,
        'page': (offset // limit) + 1,
        'page_size': limit
    }

def get_user_performance(user_id):
    """
    Per-user performance metrics.
    Returns journal count, decision count, donation trends, stage activity.
    """
    user = User.objects.get(id=user_id)

    journals = Journal.objects.filter(owner=user, is_archived=False)
    decisions = Decision.objects.filter(journal_contact__journal__owner=user)
    donations = Donation.objects.filter(contact__owner=user)

    return {
        'user': user,
        'journal_count': journals.count(),
        'decision_count': decisions.count(),
        'total_raised': donations.aggregate(Sum('amount'))['amount__sum'] or 0,
        'donation_trend': _get_donation_trend_for_user(user, months=12),
        'stage_activity': _get_stage_activity_for_user(user),
        'journals': journals.values('id', 'name', 'goal_amount', 'deadline')
    }

def _get_conversion_funnel():
    """
    Pipeline stage counts across all journals.
    """
    # Subquery: latest stage per journal_contact
    latest_stage = JournalStageEvent.objects.filter(
        journal_contact=OuterRef('pk')
    ).order_by('-created_at').values('stage')[:1]

    breakdown = JournalContact.objects.annotate(
        current_stage=Subquery(latest_stage)
    ).values('current_stage').annotate(
        count=Count('id')
    ).order_by('current_stage')

    # Map to funnel format
    stages = ['contact', 'meet', 'close', 'decision', 'thank', 'next_steps']
    funnel = {stage: 0 for stage in stages}

    for item in breakdown:
        stage = item['current_stage'] or 'contact'
        funnel[stage] = item['count']

    return [
        {'stage': stage, 'count': funnel[stage]}
        for stage in stages
    ]

def _get_team_activity(limit=10):
    """
    Recent activity across all users.
    Returns: user, event_type, contact_name, timestamp.
    """
    recent_events = Event.objects.select_related(
        'user', 'contact'
    ).order_by('-created_at')[:limit]

    return [
        {
            'user': event.user.email,
            'event_type': event.event_type,
            'contact_name': event.contact.full_name if event.contact else None,
            'timestamp': event.created_at
        }
        for event in recent_events
    ]

def _get_alerts():
    """
    Alert conditions for admin dashboard.
    - Users with 0 activity in 30 days
    - Users with 0 decisions in active journals
    - Stalled contact count threshold (>20% of contacts stalled)
    """
    stalled_count = get_stalled_contacts(limit=1)['total_count']
    total_contacts = Contact.objects.count()
    stalled_pct = (stalled_count / total_contacts * 100) if total_contacts > 0 else 0

    alerts = []

    if stalled_pct > 20:
        alerts.append({
            'severity': 'warning',
            'message': f'{stalled_count} contacts ({stalled_pct:.1f}%) are stalled'
        })

    # Add more alert conditions as needed

    return alerts
```

### Backend Views (`insights/views.py`)

```python
class AdminDashboardView(APIView):
    """
    GET: Admin dashboard overview with summary cards, funnel, activity, trends.
    """
    permission_classes = [IsAdmin]

    @extend_schema(tags=['insights'], summary='Get admin dashboard overview')
    def get(self, request):
        data = get_admin_dashboard_summary(request.user)
        return Response(data)

class StalledContactsView(APIView):
    """
    GET: Paginated list of stalled contacts (14+ days no activity).
    """
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['insights'],
        summary='Get stalled contacts',
        parameters=[
            OpenApiParameter('limit', description='Page size (default: 50)', type=int),
            OpenApiParameter('offset', description='Offset (default: 0)', type=int),
        ]
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        data = get_stalled_contacts(limit=limit, offset=offset)

        # Serialize contacts
        from apps.contacts.serializers import ContactListSerializer
        data['contacts'] = ContactListSerializer(data['contacts'], many=True).data

        return Response(data)

class UserPerformanceView(APIView):
    """
    GET: Per-user performance metrics and trends.
    """
    permission_classes = [IsAdmin]

    @extend_schema(tags=['insights'], summary='Get user performance metrics')
    def get(self, request, user_id):
        data = get_user_performance(user_id)

        # Serialize user
        from apps.users.serializers import UserSerializer
        data['user'] = UserSerializer(data['user']).data

        return Response(data)
```

### Frontend Hooks (`hooks/useAdminAnalytics.ts`)

```typescript
import { useQuery } from "@tanstack/react-query"
import {
  getAdminDashboard,
  getStalledContacts,
  getUserPerformance,
} from "@/api/adminAnalytics"

const STALE_TIME = 2 * 60 * 1000 // 2 minutes (fresher than insights)

export function useAdminDashboard() {
  return useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: getAdminDashboard,
    staleTime: STALE_TIME,
  })
}

export function useStalledContacts(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["admin", "stalled-contacts", limit, offset],
    queryFn: () => getStalledContacts(limit, offset),
    staleTime: STALE_TIME,
  })
}

export function useUserPerformance(userId: string) {
  return useQuery({
    queryKey: ["admin", "user-performance", userId],
    queryFn: () => getUserPerformance(userId),
    staleTime: STALE_TIME,
  })
}
```

---

## Query Optimization Strategy

### Problem

Cross-user aggregation queries can trigger:
- **N+1 queries** when accessing related objects in loops
- **Redundant queries** when multiple service functions query same tables
- **Slow aggregations** when not using database-level aggregation

### Solution Patterns

#### 1. Use Annotate for Aggregation

```python
# BAD: Python-level aggregation (N queries)
users = User.objects.all()
for user in users:
    user.journal_count = Journal.objects.filter(owner=user).count()
    user.decision_count = Decision.objects.filter(
        journal_contact__journal__owner=user
    ).count()

# GOOD: Database-level aggregation (1 query)
users = User.objects.annotate(
    journal_count=Count('journals', filter=Q(journals__is_archived=False)),
    decision_count=Count('journals__journal_contacts__decisions')
)
```

#### 2. Use Select Related for ForeignKey

```python
# BAD: N+1 queries when accessing contact.owner
contacts = Contact.objects.all()
for contact in contacts:
    print(contact.owner.email)  # New query per contact

# GOOD: JOIN in single query
contacts = Contact.objects.select_related('owner')
for contact in contacts:
    print(contact.owner.email)  # No additional query
```

#### 3. Use Prefetch Related for Reverse Relations

```python
# BAD: N+1 queries when accessing user.journals
users = User.objects.all()
for user in users:
    for journal in user.journals.all():  # New query per user
        print(journal.name)

# GOOD: Separate query with JOIN
users = User.objects.prefetch_related('journals')
for user in users:
    for journal in user.journals.all():  # No additional query
        print(journal.name)
```

#### 4. Use Subquery for Complex Annotations

```python
# Get latest stage event date per contact
from django.db.models import OuterRef, Subquery

latest_event = JournalStageEvent.objects.filter(
    journal_contact__contact=OuterRef('pk')
).order_by('-created_at').values('created_at')[:1]

contacts = Contact.objects.annotate(
    last_activity_date=Subquery(latest_event)
).filter(last_activity_date__lt=date.today() - timedelta(days=14))
```

#### 5. Use Values for Aggregation Results

```python
# BAD: Retrieve full ORM objects when only need aggregates
donations = Donation.objects.all()
total = sum(d.amount for d in donations)  # Loads all donation objects

# GOOD: Aggregate in database
total = Donation.objects.aggregate(Sum('amount'))['amount__sum']
```

#### 6. Combine Operations

```python
# Optimal pattern for admin dashboard
from django.db.models import Count, Sum, Q, Prefetch

users = User.objects.select_related(
    'profile'  # If User has profile ForeignKey
).prefetch_related(
    Prefetch(
        'journals',
        queryset=Journal.objects.filter(is_archived=False).annotate(
            contact_count=Count('journal_contacts'),
            decision_count=Count('journal_contacts__decisions')
        )
    )
).annotate(
    total_raised=Sum('contacts__donations__amount'),
    active_journal_count=Count('journals', filter=Q(journals__is_archived=False))
).order_by('-total_raised')

# Single query with JOINs and subqueries
```

### Avoid Known Pitfalls

From Edge Case Audit:

**1. Journal Grid N+1 (Audit 1.1):**
- Pattern: `get_stage_events()` runs query per contact
- Fix: Prefetch in view's `get_queryset()`, rewrite serializer method to use prefetched data

**2. Dashboard Redundant Queries (Audit 5.2):**
- Pattern: Each service function builds independent queryset
- Fix: Share base querysets across service functions

**3. Missing Select Related (Audit 3.6):**
- Pattern: Serializer accesses `contact.full_name` without `select_related`
- Fix: Always `select_related` for ForeignKey accessed in serializer

### Query Verification Protocol

Before deploying:

```python
# Profile query count
from django.test.utils import override_settings
from django.db import connection
from django.test import TestCase

@override_settings(DEBUG=True)
def test_admin_dashboard_query_count(self):
    response = self.client.get('/api/v1/insights/admin-dashboard/')
    queries = len(connection.queries)

    # Admin dashboard should use <20 queries regardless of user count
    self.assertLess(queries, 20)
```

Use `django-debug-toolbar` in development to verify query count per endpoint.

---

## Conversion Funnel Architecture

### Reuse Journal Pipeline Stages

The conversion funnel **IS** the journal pipeline. No new stages needed.

**Existing:** `journals/models.py:PipelineStage`
```python
class PipelineStage(models.TextChoices):
    CONTACT = 'contact', 'Contact'
    MEET = 'meet', 'Meet'
    CLOSE = 'close', 'Close'
    DECISION = 'decision', 'Decision'
    THANK = 'thank', 'Thank'
    NEXT_STEPS = 'next_steps', 'Next Steps'
```

**Admin analytics conversion funnel shows:**
- Count of contacts at each stage across ALL journals
- Stage progression rate (e.g., "60% of Meet progressed to Close")
- Time-in-stage histogram (e.g., "Average 5 days in Meet stage")

### Calculation Pattern

```python
# Get current stage per contact (latest stage event)
latest_stage = JournalStageEvent.objects.filter(
    journal_contact=OuterRef('pk')
).order_by('-created_at').values('stage')[:1]

breakdown = JournalContact.objects.annotate(
    current_stage=Subquery(latest_stage)
).values('current_stage').annotate(
    count=Count('id')
).order_by('current_stage')

# Returns: [
#   {'current_stage': 'contact', 'count': 50},
#   {'current_stage': 'meet', 'count': 30},
#   {'current_stage': 'close', 'count': 20},
#   {'current_stage': 'decision', 'count': 10},
#   ...
# ]
```

### Drill-Down Pattern

When user clicks funnel stage:

```python
# Get contacts in specific stage
if stage_param:
    latest_stage_subquery = JournalStageEvent.objects.filter(
        journal_contact=OuterRef('pk')
    ).order_by('-created_at').values('stage')[:1]

    contacts_in_stage = JournalContact.objects.annotate(
        current_stage=Subquery(latest_stage_subquery)
    ).filter(
        current_stage=stage_param
    ).select_related(
        'contact__owner',
        'journal__owner'
    ).values(
        'contact__id',
        'contact__full_name',
        'contact__owner__email',
        'journal__name'
    )
```

Frontend displays list of contacts in modal/panel with links to contact detail.

---

## Stalled Contact Detection Algorithm

### Definition

A contact is "stalled" when:
- Contact is in a journal (has JournalContact record)
- Last JournalStageEvent for that contact is >14 days ago
- OR contact has no stage events at all (added to journal but no activity)

### Implementation

```python
from datetime import date, timedelta
from django.db.models import OuterRef, Subquery, Q

def get_stalled_contacts(limit=50, offset=0):
    """
    Detect stalled contacts with 14+ days inactivity.
    """
    cutoff_date = date.today() - timedelta(days=14)

    # Subquery: latest stage event timestamp per contact
    latest_event = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    # Annotate contacts with last activity date
    stalled = Contact.objects.annotate(
        last_activity_date=Subquery(latest_event)
    ).filter(
        # Contact is in at least one journal
        journal_contacts__isnull=False
    ).filter(
        # AND (last activity >14 days OR no activity)
        Q(last_activity_date__lt=cutoff_date) |
        Q(last_activity_date__isnull=True)
    ).distinct().select_related('owner').order_by('last_activity_date')

    total = stalled.count()
    contacts = stalled[offset:offset+limit]

    return {
        'contacts': contacts,
        'total_count': total,
        'page': (offset // limit) + 1,
        'page_size': limit
    }
```

### Edge Cases

**1. Contact in multiple journals:**
- Use latest event across ALL journals
- Subquery already handles this: `journal_contact__contact=OuterRef('pk')` matches all journal_contacts for contact

**2. Contact added to journal but never had stage event:**
- Filter catches `last_activity_date__isnull=True`
- These appear at bottom of list (NULL sorts last with `order_by('last_activity_date')`)

**3. Archived journals:**
- Should stalled detection ignore archived journals?
- **Decision:** Include archived journals. If contact was active in archived journal, they're not stalled.
- To exclude archived: add `.filter(journal_contact__journal__is_archived=False)` to subquery

### Performance Consideration

Subquery runs once per page of results. With 50 contacts per page and proper indexes:
- Subquery is efficient (single scan of JournalStageEvent with index on journal_contact + created_at)
- `distinct()` deduplicates contacts in multiple journals
- Total query time: <100ms for 50 contacts

Index needed:
```python
# In JournalStageEvent model
class Meta:
    indexes = [
        models.Index(fields=['journal_contact', '-created_at']),
    ]
```

---

## Pace Calculation Logic

### Definition

"Pace" measures how quickly a contact is progressing through the pipeline.

**Metric:** Average days between stage transitions.

### Calculation

```python
def calculate_pace(contact_id, journal_id):
    """
    Calculate average days between stage transitions for a contact.
    """
    events = JournalStageEvent.objects.filter(
        journal_contact__contact_id=contact_id,
        journal_contact__journal_id=journal_id
    ).order_by('created_at').values('stage', 'created_at')

    if len(events) < 2:
        return None  # Need at least 2 events to calculate pace

    transitions = []
    for i in range(1, len(events)):
        prev_event = events[i-1]
        curr_event = events[i]

        days_between = (curr_event['created_at'] - prev_event['created_at']).days
        transitions.append(days_between)

    avg_pace = sum(transitions) / len(transitions)

    return {
        'avg_days_per_stage': avg_pace,
        'total_transitions': len(transitions),
        'fastest_transition': min(transitions),
        'slowest_transition': max(transitions)
    }
```

### Display

- User detail page shows pace metric per missionary
- Stalled contacts page can sort by pace (slowest first = most stalled)

### Alternative: Time-in-Current-Stage

Simpler metric:

```python
def time_in_current_stage(contact_id, journal_id):
    """
    Days since contact entered current stage.
    """
    latest_event = JournalStageEvent.objects.filter(
        journal_contact__contact_id=contact_id,
        journal_contact__journal_id=journal_id
    ).order_by('-created_at').first()

    if not latest_event:
        return None

    days = (date.today() - latest_event.created_at.date()).days

    return {
        'current_stage': latest_event.stage,
        'days_in_stage': days
    }
```

This is more actionable: "Contact has been in Meet stage for 21 days."

**Recommendation:** Use time-in-current-stage for v1.2. Add full pace calculation in future if needed.

---

## Build Order

### Phase 1: Backend Foundation

**Goal:** Core analytics endpoints functional, testable via API.

1. **Extend `insights/services.py`** with new service functions:
   - `get_admin_dashboard_summary()`
   - `get_stalled_contacts()`
   - `get_user_performance()`
   - `_get_conversion_funnel()`
   - `_get_team_activity()`

2. **Add views to `insights/views.py`**:
   - `AdminDashboardView`
   - `StalledContactsView`
   - `UserPerformanceView`

3. **Extend `insights/urls.py`** with new paths

4. **Add indexes** to `JournalStageEvent` model

5. **Write tests** for each service function (query count, correct results, permission checks)

**Dependencies:** None. Builds on existing models and permission classes.

**Validation:** Test via API client (Postman, Swagger UI) before starting frontend.

---

### Phase 2: Frontend Foundation

**Goal:** Pages render with data from API.

1. **Add API client functions** in `api/adminAnalytics.ts`:
   - `getAdminDashboard()`
   - `getStalledContacts()`
   - `getUserPerformance()`

2. **Add React Query hooks** in `hooks/useAdminAnalytics.ts`

3. **Create placeholder pages**:
   - `pages/admin/AdminAnalyticsDashboard.tsx` — render summary cards only
   - `pages/admin/StalledContacts.tsx` — render table only
   - `pages/admin/UserPerformance.tsx` — render basic metrics only

4. **Add routes** to `App.tsx` with `requiredRole="admin"`

5. **Update navigation** in `AppLayout.tsx` to add Analytics submenu

**Dependencies:** Phase 1 complete (API endpoints working).

**Validation:** Pages load with real data from API.

---

### Phase 3: Dashboard Widgets

**Goal:** Overview page has all widgets functional.

1. **Build chart components**:
   - `components/analytics/ConversionFunnelChart.tsx` (Recharts BarChart)
   - `components/analytics/TrendChart.tsx` (Recharts LineChart)
   - `components/analytics/TeamActivityTable.tsx` (React Table)

2. **Build layout components**:
   - Summary cards grid
   - Two-column layout (funnel left, trend right)
   - Activity table below

3. **Add alerts panel** (severity badges, message list)

4. **Wire up** all components in `AdminAnalyticsDashboard.tsx`

**Dependencies:** Phase 2 complete (API hooks working).

**Validation:** Dashboard page matches mockup, all widgets display data.

---

### Phase 4: Stalled Contacts Page

**Goal:** Stalled contacts page with pagination and sorting.

1. **Build table** with React Table:
   - Columns: Contact Name, Owner, Days Since Activity, Current Stage, Actions
   - Sortable by days since activity
   - Pagination controls

2. **Add filtering** (optional):
   - By owner (dropdown)
   - By days threshold (slider: 14, 30, 60 days)

3. **Add actions**:
   - View contact (link to contact detail)
   - View journal (link to journal detail)

**Dependencies:** Phase 2 complete (API hooks working).

**Validation:** Stalled contacts page loads, pagination works, sorting works.

---

### Phase 5: User Performance Page

**Goal:** Per-user detail page with trends and journals.

1. **Build user header** (name, email, role, summary metrics)

2. **Build trend charts**:
   - Donation trend (12 months)
   - Stage activity (6 stages over time)

3. **Build journals table** (name, goal, deadline, progress)

4. **Add navigation** from team activity table to user detail page

**Dependencies:** Phase 2 complete (API hooks working).

**Validation:** User detail page loads, charts display, journals listed.

---

### Phase 6: Drill-Down Interactions

**Goal:** Click funnel segment to see underlying contacts.

1. **Add click handler** to `ConversionFunnelChart`:
   - Capture clicked stage
   - Open `UserDrilldownPanel` with contact list

2. **Build `UserDrilldownPanel`**:
   - Slide-in sidebar (Radix Dialog or Sheet)
   - Contact list with links to contact detail
   - Close button

3. **Add drill-down endpoint** (extend `ConversionFunnelView` to accept `?stage=decision`)

4. **Wire up** panel to funnel chart

**Dependencies:** Phase 3 complete (funnel chart working).

**Validation:** Click funnel stage, panel opens with contact list.

---

### Phase 7: Polish & Optimization

**Goal:** Production-ready performance and UX.

1. **Query optimization audit**:
   - Run `django-debug-toolbar` on each endpoint
   - Verify query count <20 per endpoint
   - Add missing `select_related`/`prefetch_related`

2. **Loading states**:
   - Skeleton loaders for charts (Recharts has built-in loading state)
   - Table loading spinner

3. **Error handling**:
   - API error toast notifications
   - Empty state messages ("No stalled contacts — great work!")

4. **Accessibility**:
   - ARIA labels on charts
   - Keyboard navigation for drill-down panels

5. **Responsive design**:
   - Mobile layout for admin pages (if needed)
   - Chart responsiveness (Recharts ResponsiveContainer)

**Dependencies:** Phases 1-6 complete.

**Validation:** Performance audit passes, UX polished.

---

## Suggested Build Order Rationale

**1. Backend first (Phase 1):**
- API endpoints are testable independently
- Catches data modeling issues early
- Frontend can develop against real API, not mocks

**2. Foundation before features (Phase 2):**
- Routing and navigation working before complex widgets
- Validates API integration early
- Reduces context switching

**3. Dashboard before detail pages (Phase 3-4):**
- Dashboard is the landing page, highest priority
- Stalled contacts page is simpler (table-only), good second page
- User performance page reuses patterns from dashboard

**4. Drill-down last (Phase 6):**
- Enhancement, not MVP requirement
- Requires both funnel chart and panel working
- Can be deferred if timeline tight

**5. Polish always last (Phase 7):**
- Performance optimization requires full feature set
- UX polish needs user feedback

---

## Anti-Patterns to Avoid

### 1. Aggregating in Python Instead of Database

**Bad:**
```python
users = User.objects.all()
for user in users:
    user.journal_count = Journal.objects.filter(owner=user).count()
```

**Good:**
```python
users = User.objects.annotate(journal_count=Count('journals'))
```

### 2. Separate Apps for Single Feature

**Bad:**
- Create `admin_analytics` app with 5 views
- Separate URL namespace, separate permission classes
- Confusion: "Is this insights or admin_analytics?"

**Good:**
- Extend `insights` app with new views
- Reuse existing permission classes
- Clear boundary: `insights` = all analytics/reports

### 3. Duplicating Existing Analytics Endpoints

**Bad:**
- Create new `AdminConversionFunnelView` that duplicates `JournalAnalyticsViewSet.pipeline_breakdown`

**Good:**
- Extend existing endpoint with query params: `?user_id=all` or `?scope=admin`
- Reuse service functions with role-based filtering

### 4. Frontend Routes Mixing Admin and Insights

**Bad:**
- `/insights/admin-dashboard`
- `/admin/stalled-contacts`
- Inconsistent: admin analytics split between two top-level routes

**Good:**
- All admin analytics under `/admin/analytics/*`
- Matches existing admin pages pattern
- Clear hierarchy

### 5. N+1 Queries in Serializers

**Bad:**
```python
class ContactSerializer:
    def get_owner_email(self, obj):
        return obj.owner.email  # Query per contact if not select_related
```

**Good:**
```python
# In view
queryset = Contact.objects.select_related('owner')

# Serializer can safely access obj.owner.email
```

### 6. Missing Pagination on Large Result Sets

**Bad:**
```python
# Return all stalled contacts (could be 1000+)
def get_stalled_contacts():
    return Contact.objects.filter(...)
```

**Good:**
```python
# Paginate with limit/offset
def get_stalled_contacts(limit=50, offset=0):
    qs = Contact.objects.filter(...)
    total = qs.count()
    return {
        'contacts': qs[offset:offset+limit],
        'total_count': total
    }
```

---

## Scalability Considerations

| Concern | At 10 users | At 100 users | At 500 users |
|---------|-------------|--------------|--------------|
| Conversion funnel query | <50ms | <200ms | <500ms |
| Stalled contacts (50 per page) | <100ms | <300ms | <800ms |
| Dashboard overview | <200ms | <500ms | 1-2s |
| Mitigation | — | Add indexes | Add caching (Redis, 2min TTL) |

### Caching Strategy (Future)

If dashboard queries exceed 1s at scale:

```python
from django.core.cache import cache

def get_admin_dashboard_summary(user):
    cache_key = 'admin_dashboard_summary'
    cached = cache.get(cache_key)

    if cached:
        return cached

    data = {
        'summary_cards': _get_summary_cards(),
        'conversion_funnel': _get_conversion_funnel(),
        # ...
    }

    cache.set(cache_key, data, timeout=120)  # 2 minute TTL
    return data
```

Invalidate cache on:
- New JournalStageEvent created
- New Decision created
- New Donation created

Or use time-based TTL (2-5 minutes) if real-time updates not critical.

---

## Sources

**Django Optimization:**
- [Database access optimization | Django documentation](https://docs.djangoproject.com/en/6.0/topics/db/optimization/)
- [Optimizing Django Queries with select_related and prefetch_related](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)
- [Django QuerySet Optimization: Stop Strangling Your API Performance](https://medium.com/@sizanmahmud08/django-queryset-optimization-stop-stranglingyour-api-performance-6bc368d72512)

**Analytics Architecture:**
- [SaaS Applications with Django: Building Analytics and Dashboards](https://medium.com/@mathur.danduprolu/saas-applications-with-django-building-analytics-and-dashboards-part-5-7-5e5e11ec310a)
- [Scale Your Django API Like a Pro: The Complete 2026 Guide](https://medium.com/@sizanmahmud08/scale-your-django-api-like-a-pro-the-complete-2026-guide-to-handling-millions-of-requests-f0d3362f767d)
- [How to create an analytics dashboard in a Django app](https://www.freecodecamp.org/news/how-to-create-an-analytics-dashboard-in-django-app/)

**API Design:**
- [APIView vs ViewSet in Django REST Framework](https://medium.com/@mathur.danduprolu/apiview-vsviewset-in-django-rest-framework-aa9a77921d53)
- [Build scalable APIs with Django REST API framework](https://www.kellton.com/kellton-tech-blog/designing-rest-apis-with-django-rest-api-framework)

**Dashboard Architecture:**
- [Six Principles of Dashboard Information Architecture](https://www.gooddata.com/blog/six-principles-of-dashboard-information-architecture/)
- [Single App vs. Multiple Apps: Choosing the Right Approach](https://medium.com/@bharathibala21/single-app-vs-multiple-apps-choosing-the-right-approach-for-your-mobile-application-b0d8d420d998)

**Conversion Funnel:**
- [Conversion Funnel: The Ultimate Guide to Stages & Optimization (2026)](https://improvado.io/blog/conversion-funnel)
- [Pipeline Funnel Visual](https://docs.visier.com/developer/Analytics/visual%20types/pipeline%20funnel.htm)
