# Phase 13: Backend Foundation & Security - Research

**Researched:** 2026-02-12
**Domain:** Django REST Framework analytics endpoints, database-level aggregation, permission enforcement, race condition mitigation
**Confidence:** HIGH

## Summary

Phase 13 extends the existing `apps/insights/` app (7 views, 7 service functions) with 5 new admin analytics endpoints using database-level aggregation patterns already established in the codebase. Research focused on understanding the current state of the codebase to identify what exists, what patterns are already in use, and what critical pitfalls must be fixed.

**Key findings:**
1. **Existing foundation is strong**: `apps/insights/` already has owner-scoped service functions, admin role checks, and database aggregation patterns using `annotate()`/`aggregate()` with `TruncMonth`/`TruncYear`/`Sum`/`Count`.
2. **Critical vulnerabilities exist**: Edge Case Audit identifies 6 security/data integrity issues that MUST be fixed in this phase, including ListAPIView permission bypass, race conditions in `update_giving_stats()` and `record_fulfillment()`, and `is_staff` vs `role=='admin'` inconsistency.
3. **Existing patterns for reuse**: Journal analytics already demonstrates cross-user aggregation (`admin_summary`), Subquery for latest events (`pipeline_breakdown`), and admin-only endpoint patterns.

**Primary recommendation:** Extend `apps/insights/views.py` and `apps/insights/services.py` with new admin analytics functions following existing patterns. Fix critical vulnerabilities in same phase to ensure secure foundation.

## Standard Stack

The codebase already uses the standard Django REST Framework analytics stack:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | 4.2+ | Database aggregation with `annotate()`, `aggregate()`, `Subquery`, `OuterRef`, `F()` expressions | Native Django solution, already used in 6+ aggregation endpoints |
| DRF generics | 3.14+ | APIView base classes for analytics endpoints | All existing analytics use `APIView`, not ViewSets (except `JournalAnalyticsViewSet`) |
| drf-spectacular | 0.26+ | OpenAPI schema with `@extend_schema` decorators | Already configured, used on all 162 existing views |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django.db.models functions | builtin | `TruncMonth`, `TruncYear`, `TruncDate` for time-series aggregation | Already used in `get_donations_by_month()`, `decision_trends()`, 3+ other endpoints |
| dateutil.relativedelta | 2.8+ | Date arithmetic for date ranges | Already installed, used in pledge calculations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APIView pattern | ViewSet with @action | Existing `JournalAnalyticsViewSet` uses this pattern, but `insights` app uses APIView — consistency favors APIView |
| Database aggregation | Python aggregation | Database aggregation avoids N+1 queries — required for <20 query target |

**Installation:**
No new dependencies required. All libraries already installed and in use.

## Architecture Patterns

### Existing Analytics Endpoint Structure

The codebase has TWO analytics patterns:

**Pattern A: insights app (7 endpoints)**
```
apps/insights/
├── views.py         # APIView classes, one per endpoint
├── services.py      # Business logic functions (_scope_*, get_*)
└── urls.py          # path() registration
```

**Pattern B: journals app (5 analytics endpoints)**
```
apps/journals/
└── views.py         # JournalAnalyticsViewSet with @action decorators
```

**For Phase 13:** Use Pattern A (insights app) because:
- Requirements specify "extend existing insights app"
- Insights app already has 7 endpoints using this pattern
- Adding 5 more fits naturally

### Recommended Project Structure for New Endpoints
```
apps/insights/
├── views.py                    # Add 5 new APIView classes
│   ├── DashboardOverviewView (admin-only)
│   ├── StalledContactsView (admin-only)
│   ├── UserPerformanceView (admin-only)
│   ├── ConversionFunnelView (admin-only)
│   └── TeamActivityView (admin-only)
├── services.py                 # Add 5 new service functions
│   ├── get_dashboard_overview()
│   ├── get_stalled_contacts()
│   ├── get_user_performance()
│   ├── get_conversion_funnel()
│   └── get_team_activity()
└── urls.py                     # Add 5 new path() registrations
```

### Pattern 1: Database-Level Aggregation (REQUIRED)

**What:** Use Django ORM's `annotate()` and `aggregate()` to perform calculations in PostgreSQL, not Python.

**When to use:** Always for analytics endpoints. Target <20 queries per endpoint (per requirement API-03).

**Example from existing codebase:**
```python
# Source: apps/insights/services.py:37-56
def get_donations_by_month(user, year=None):
    if year is None:
        year = date.today().year

    donations = _scope_donations(user)

    monthly_data = (
        donations.filter(date__year=year)
        .annotate(month=TruncMonth('date'))  # Database-level date truncation
        .values('month')
        .annotate(                           # Database-level aggregation
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('month')
    )

    # Build complete 12-month list (fill gaps with 0) in Python
    # This is acceptable because we're working with 12 rows, not N rows
```

**Query count:** 1 query for aggregation + queryset construction = <5 total.

### Pattern 2: Subquery for Latest Event Per Entity

**What:** Use `Subquery` and `OuterRef` to annotate each entity with its most recent related object's value.

**When to use:** Finding "last activity date" or "current stage" per contact.

**Example from existing codebase:**
```python
# Source: apps/journals/views.py:483-495
def pipeline_breakdown(self, request):
    # Subquery to get most recent stage per journal_contact
    latest_stage = JournalStageEvent.objects.filter(
        journal_contact=OuterRef('pk')
    ).order_by('-created_at').values('stage')[:1]

    jc_qs = JournalContact.objects.all() if self._is_admin(request) else JournalContact.objects.filter(
        journal__owner=request.user
    )
    breakdown = jc_qs.annotate(
        current_stage=Subquery(latest_stage)  # Annotate with subquery result
    ).values('current_stage').annotate(
        count=Count('id')
    ).order_by('current_stage')

    return Response([...])
```

**Query count:** 1 query with subquery annotation = efficient.

**For stalled contacts (requirement API-04):**
```python
# Use Subquery to find contacts with last JournalStageEvent >14 days ago
last_activity = JournalStageEvent.objects.filter(
    journal_contact__contact=OuterRef('pk')
).order_by('-created_at').values('created_at')[:1]

stalled = Contact.objects.annotate(
    last_activity_date=Subquery(last_activity)
).filter(
    last_activity_date__lt=timezone.now() - timedelta(days=14)
)
```

### Pattern 3: Owner-Scoped Data with Admin Override

**What:** Service functions check `user.role` and return scoped queryset.

**When to use:** All analytics endpoints where data is owner-scoped.

**Example from existing codebase:**
```python
# Source: apps/insights/services.py:16-21
def _scope_donations(user):
    """Return donation queryset scoped by user role."""
    if user.role in ['admin', 'finance', 'read_only']:
        return Donation.objects.all()
    return Donation.objects.filter(contact__owner=user)
```

**For admin analytics:** Admin-only endpoints don't need per-user scoping — they aggregate across ALL users.

### Pattern 4: Admin-Only Endpoint Pattern

**What:** Permission class checks `role == 'admin'` at view level, service function operates on unfiltered data.

**When to use:** Cross-user aggregation endpoints (all 5 new endpoints in Phase 13).

**EXISTING VULNERABLE PATTERN (DO NOT COPY):**
```python
# Source: apps/journals/views.py:532-540 (WRONG PATTERN)
@action(detail=False, methods=['get'], url_path='admin-summary')
def admin_summary(self, request):
    """Cross-missionary aggregation data (admin only)."""
    # Check if user is staff
    if not request.user.is_staff:  # ❌ WRONG: uses is_staff not role
        return Response(
            {'detail': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
```

**CORRECT PATTERN:**
```python
# Use IsAdmin permission class (apps/core/permissions.py:7-15)
from apps.core.permissions import IsAdmin

class DashboardOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(tags=['insights'], summary='Admin dashboard overview')
    def get(self, request):
        return Response(get_dashboard_overview())
```

**Why IsAdmin is better:**
1. DRF permission classes run before view method executes
2. Returns proper 403 with DRF's error format
3. Consistent with other admin-only endpoints (e.g., `ReviewQueueView`, `TransactionsView`)
4. Fixes Edge Case Audit issue 1.5 (is_staff vs role inconsistency)

### Pattern 5: Conversion Funnel with Existing Pipeline

**What:** Reuse journal 6-stage pipeline (`PipelineStage` choices) for funnel visualization.

**When to use:** Requirement API-05 specifies conversion funnel reuses journal pipeline.

**Existing pipeline stages (source: apps/journals/models.py:14-22):**
```python
class PipelineStage(models.TextChoices):
    CONTACT = 'contact', 'Contact'
    MEET = 'meet', 'Meet'
    CLOSE = 'close', 'Close'
    DECISION = 'decision', 'Decision'
    THANK = 'thank', 'Thank'
    NEXT_STEPS = 'next_steps', 'Next Steps'
```

**Funnel aggregation pattern:**
```python
# Count contacts in each stage (most recent stage per contact)
latest_stage = JournalStageEvent.objects.filter(
    journal_contact=OuterRef('pk')
).order_by('-created_at').values('stage')[:1]

funnel = JournalContact.objects.annotate(
    current_stage=Subquery(latest_stage)
).values('current_stage').annotate(
    count=Count('id')
).order_by('current_stage')
```

### Anti-Patterns to Avoid

- **Manual role check in view method:** Use permission classes, not `if request.user.role == 'admin'` inside view
- **Python aggregation:** Don't iterate queryset in Python to calculate sums/counts — use `aggregate()`
- **N+1 queries in serializer:** Don't access related objects per-row — use `select_related()` / `prefetch_related()` in view queryset
- **ListAPIView with object-level permissions only:** DRF never calls `has_object_permission()` on list views — add queryset filtering
- **is_staff check for admin role:** Use `role == 'admin'` consistently

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Role-based access control | Manual checks in view methods | `IsAdmin`, `IsFinanceOrAdmin`, `IsStaffOrAbove` permission classes | Already exists in `apps/core/permissions.py`, properly returns 403 before view executes |
| Cross-user aggregation | Loop through users in Python | `annotate()` with no owner filter | Database does it in one query |
| Latest event per entity | Fetch all events, filter in Python | `Subquery` with `OuterRef` and `[:1]` slice | Requirement API-04 specifically requires this pattern |
| Date range grouping | Manual date bucketing | `TruncMonth`, `TruncYear`, `TruncDate` | Already used in 3+ existing endpoints |
| Query optimization | Manual select_related on each queryset | Establish pattern in view's `get_queryset()` | Centralized, consistent |

**Key insight:** The codebase already has all patterns needed for Phase 13. Don't invent new patterns — extend existing ones.

## Common Pitfalls

### Pitfall 1: ListAPIView Permission Bypass (CRITICAL)

**What goes wrong:** Object-level permission classes (`has_object_permission()`) are never called on `ListAPIView` because DRF only calls them in `get_object()`, which list views don't use.

**Why it happens:** Misunderstanding of DRF's permission architecture. Developers add `IsContactOwnerOrReadAccess` to a list view, expect it to filter results, but it never runs.

**Existing vulnerability in codebase (Edge Case Audit issue 2.2):**
```python
# apps/contacts/views.py:139-153
class ContactDonationsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsContactOwnerOrReadAccess]

    def get_queryset(self):
        contact_id = self.kwargs.get('pk')
        return Donation.objects.filter(contact_id=contact_id).order_by('-date')
        # ❌ No owner filter — any user can see any contact's donations
```

**How to avoid:**
1. **For admin-only endpoints:** Use `IsAdmin` permission class (enforces at view level, no list bypass)
2. **For owner-scoped endpoints:** Add explicit owner filtering in `get_queryset()`

**Warning signs:**
- Object-level permission class on a ListView/ListAPIView
- No owner filter in `get_queryset()`
- Permission tests pass for detail views but not tested for list views

**Fix for Phase 13:** All new endpoints are admin-only, so use `IsAdmin` permission class — no list bypass possible.

### Pitfall 2: Race Condition in update_giving_stats() (CRITICAL)

**What goes wrong:** Multiple concurrent calls to `update_giving_stats()` read stale data and overwrite each other's updates.

**Why it happens:** Method reads aggregate stats, modifies instance fields, saves — classic read-modify-write race.

**Existing vulnerability (Edge Case Audit issue 2.1):**
```python
# apps/contacts/models.py:152-181
def update_giving_stats(self):
    donations = self.donations.all()
    agg = donations.aggregate(...)  # Read

    self.total_given = agg['total'] or 0  # Modify
    self.gift_count = agg['count'] or 0
    # ... more field updates

    self.save(update_fields=[...])  # Write
```

**Trigger scenario:** Bulk CSV import creates 50 donations for same contact. Each `post_save` signal calls `update_giving_stats()`. Last write wins, intermediate updates lost.

**How to avoid:**
1. **During bulk import:** Disable signals with `@receiver(post_save, sender=Donation)` decorator check, manually call `update_giving_stats()` once after import completes
2. **For single updates:** Use `F()` expressions for atomic updates: `Contact.objects.filter(pk=self.pk).update(total_given=F('total_given') + amount)`
3. **For complex recalculations:** Use `select_for_update()` to lock row during recalculation

**Warning signs:**
- Aggregate calculation inside model method that calls `save()`
- Signal handler that triggers on every related object create
- Bulk operations without signal disabling

**Fix for Phase 13:** Not directly fixing this (that's a separate refactor), but documenting as known issue that affects data quality of analytics endpoints.

### Pitfall 3: Race Condition in record_fulfillment() (HIGH)

**What goes wrong:** `self.total_received += donation.amount` is read-modify-write. Two concurrent calls lose one donation amount.

**Why it happens:** Same as Pitfall 2 — read-modify-write without locking.

**Existing vulnerability (Edge Case Audit issue 3.2):**
```python
# apps/pledges/models.py:191-198
def record_fulfillment(self, donation):
    self.last_fulfilled_date = donation.date
    self.total_received += donation.amount  # ❌ Read-modify-write race
    self.next_expected_date = self.calculate_next_expected_date()
    self.is_late = False
    self.days_late = 0
    self.save()
```

**How to avoid:** Use `F()` expression for atomic increment:
```python
Pledge.objects.filter(pk=self.pk).update(
    total_received=F('total_received') + donation.amount,
    last_fulfilled_date=donation.date,
    # ... other fields
)
self.refresh_from_db()
```

**Warning signs:**
- `+=` operator on model field before `save()`
- Called from signal handler (concurrent execution possible)
- No `select_for_update()` locking

**Fix for Phase 13:** Requirements specify "fix existing race conditions" — this MUST be fixed in this phase.

### Pitfall 4: is_staff vs role Inconsistency (MODERATE)

**What goes wrong:** User passes one check but fails another due to inconsistent role checking.

**Why it happens:** Django's built-in `is_staff` flag vs custom `role` field confusion.

**Existing vulnerability (Edge Case Audit issue 1.5):**
```python
# apps/journals/views.py:536
if not request.user.is_staff:  # ❌ Every other admin check uses role == 'admin'
    return Response({'detail': 'Admin access required'}, status=403)
```

**User model has TWO admin indicators:**
- `is_staff` (Django builtin, for Django admin site access)
- `role` (custom field, values: 'staff', 'admin', 'finance', 'read_only')

**Codebase standard:** Use `role == 'admin'` for business logic admin checks. 158/159 checks use `role`, only 1 uses `is_staff`.

**How to avoid:**
1. Always use `role == 'admin'` for admin access checks
2. Use `IsAdmin` permission class (already checks `role == 'admin'`)
3. Never check `is_staff` for business logic — it's for Django admin only

**Warning signs:**
- `request.user.is_staff` in view code
- Direct role check instead of permission class

**Fix for Phase 13:** Update existing `admin_summary` endpoint to use `IsAdmin` permission class, ensure all new endpoints use `IsAdmin`.

### Pitfall 5: Unbounded Result Sets in Analytics (MODERATE)

**What goes wrong:** Analytics endpoint returns years of data with no pagination or date windowing.

**Why it happens:** Forgot to add date range filter or limit.

**Existing issue (Edge Case Audit issue 1.4):** `decision_trends()` and `stage_activity()` return full result sets.

**How to avoid:**
1. Add default date range (e.g., last 12 months) to time-series endpoints
2. Add `[:limit]` slice to list-style endpoints (e.g., stalled contacts)
3. Document in API schema what the default range is

**Warning signs:**
- No `.filter(date__gte=...)` on time-series aggregation
- No `[:N]` slice on queryset
- No mention of date range in docstring

**Fix for Phase 13:** All new endpoints should have explicit limits or date ranges.

## Code Examples

Verified patterns from official sources:

### Admin-Only Endpoint with Database Aggregation

```python
# Pattern: apps/insights/views.py (extend this file)
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsAdmin
from apps.insights.services import get_dashboard_overview

class DashboardOverviewView(APIView):
    """
    GET: Get admin dashboard overview with cross-user aggregation.
    Admin-only endpoint.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=['insights'],
        summary='Get dashboard overview (admin only)',
        description='Cross-user aggregation for admin dashboard'
    )
    def get(self, request):
        return Response(get_dashboard_overview())
```

### Service Function with Database Aggregation

```python
# Pattern: apps/insights/services.py (extend this file)
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from apps.contacts.models import Contact
from apps.donations.models import Donation

def get_dashboard_overview():
    """
    Get admin dashboard overview.
    No user scoping - admin sees all data.
    """
    # Single aggregation query
    stats = Donation.objects.aggregate(
        total_amount=Sum('amount'),
        total_count=Count('id')
    )

    # Time-series aggregation (last 12 months)
    from datetime import date
    from dateutil.relativedelta import relativedelta

    start_date = date.today() - relativedelta(months=12)
    monthly = Donation.objects.filter(
        date__gte=start_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('month')

    return {
        'total_donations': stats['total_count'],
        'total_amount': float(stats['total_amount'] or 0),
        'monthly_trend': [
            {'month': m['month'].strftime('%Y-%m'), 'total': float(m['total'])}
            for m in monthly
        ]
    }
```

### Stalled Contacts with Subquery Annotation

```python
# Pattern for requirement API-04
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from datetime import timedelta
from apps.contacts.models import Contact
from apps.journals.models import JournalStageEvent

def get_stalled_contacts(limit=50):
    """
    Find contacts with last journal activity >14 days ago.
    Uses Subquery annotation per requirement API-04.
    """
    # Subquery to get last activity date per contact
    last_activity = JournalStageEvent.objects.filter(
        journal_contact__contact=OuterRef('pk')
    ).order_by('-created_at').values('created_at')[:1]

    cutoff_date = timezone.now() - timedelta(days=14)

    stalled = Contact.objects.annotate(
        last_activity_date=Subquery(last_activity)
    ).filter(
        last_activity_date__lt=cutoff_date,
        last_activity_date__isnull=False  # Exclude contacts with no activity
    ).select_related('owner').order_by('last_activity_date')[:limit]

    return {
        'stalled_contacts': [
            {
                'id': str(c.id),
                'full_name': c.full_name,
                'owner_email': c.owner.email,
                'last_activity_date': c.last_activity_date.isoformat(),
                'days_stalled': (timezone.now() - c.last_activity_date).days,
            }
            for c in stalled
        ],
        'total_count': Contact.objects.annotate(
            last_activity_date=Subquery(last_activity)
        ).filter(last_activity_date__lt=cutoff_date).count()
    }
```

### F() Expression for Atomic Update (Race Condition Fix)

```python
# Fix for apps/pledges/models.py:191-198
from django.db.models import F

def record_fulfillment(self, donation):
    """Record that a donation fulfilled this pledge period."""
    # Atomic update using F() expression
    Pledge.objects.filter(pk=self.pk).update(
        last_fulfilled_date=donation.date,
        total_received=F('total_received') + donation.amount,  # Atomic increment
        next_expected_date=self.calculate_next_expected_date(),
        is_late=False,
        days_late=0
    )
    # Refresh instance to get updated values
    self.refresh_from_db()
```

### URL Registration

```python
# Pattern: apps/insights/urls.py (extend this file)
from django.urls import path
from apps.insights.views import (
    DashboardOverviewView,
    StalledContactsView,
    UserPerformanceView,
    ConversionFunnelView,
    TeamActivityView,
)

app_name = 'insights'

urlpatterns = [
    # ... existing 7 endpoints ...

    # Admin analytics (Phase 13)
    path('admin/dashboard-overview/', DashboardOverviewView.as_view(), name='admin-dashboard'),
    path('admin/stalled-contacts/', StalledContactsView.as_view(), name='admin-stalled'),
    path('admin/user-performance/', UserPerformanceView.as_view(), name='admin-performance'),
    path('admin/conversion-funnel/', ConversionFunnelView.as_view(), name='admin-funnel'),
    path('admin/team-activity/', TeamActivityView.as_view(), name='admin-activity'),
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual role checks in view methods | Permission classes (`IsAdmin`, `IsStaffOrAbove`) | Established in initial build | Consistent 403 responses, cleaner code |
| Python aggregation (loops over querysets) | Database-level `annotate()`/`aggregate()` | Established in insights app (Phase 6) | <20 queries per endpoint possible |
| Object-level permissions on list views | Explicit queryset filtering in `get_queryset()` | Not yet standardized — Edge Case Audit identified as vulnerability | Phase 13 must establish secure pattern |
| `is_staff` for admin checks | `role == 'admin'` | Mostly migrated (158/159 checks), 1 outlier remains | Phase 13 fixes last outlier |

**Deprecated/outdated:**
- ❌ `is_staff` for business logic admin checks — use `role == 'admin'`
- ❌ Object-level permission classes on ListAPIView without queryset filtering — add explicit owner filter
- ❌ Read-modify-write without F() expressions — use atomic updates

## Current State Assessment

### What Exists in apps/insights/

**Files:**
- `views.py` (162 lines, 7 APIView classes)
- `services.py` (301 lines, 9 functions)
- `urls.py` (27 lines, 7 path registrations)
- `apps.py` (configuration)

**Existing endpoints (7):**
1. `DonationsByMonthView` — owner-scoped, time-series aggregation
2. `DonationsByYearView` — owner-scoped, time-series aggregation
3. `MonthlyCommitmentsView` — owner-scoped, pledge summary
4. `LateDonationsView` — owner-scoped, filtered pledge list
5. `FollowUpsView` — owner-scoped, task list
6. `ReviewQueueView` — admin-only (manual check in view, not permission class)
7. `TransactionsView` — admin/finance (manual check in view, not permission class)

**Existing service patterns:**
- `_scope_donations(user)` — returns queryset scoped by role
- `_scope_pledges(user)` — returns queryset scoped by role
- `_scope_tasks(user)` — returns queryset scoped by role
- All service functions accept `user` parameter for scoping

**Observation:** Existing admin endpoints (ReviewQueueView, TransactionsView) use manual `if request.user.role != 'admin'` checks in view method. Phase 13 should standardize on permission classes instead.

### What Exists in apps/core/permissions.py

**Permission classes (6):**
1. `IsAdmin` — checks `role == 'admin'` in `has_permission()`
2. `IsFinanceOrAdmin` — checks `role in ['admin', 'finance']`
3. `IsStaffOrAbove` — checks `role in ['admin', 'finance', 'staff']`, allows read-only for SAFE_METHODS
4. `IsOwnerOrAdmin` — object-level, checks `obj.owner == user or role == 'admin'`
5. `IsContactOwnerOrReadAccess` — object-level, checks contact ownership with finance/read-only read access
6. `ReadOnlyOrAdmin` — view-level, SAFE_METHODS for all, full access for admin

**Observation:** `IsAdmin` exists and is correct pattern for Phase 13 admin endpoints.

### What Exists in Race Condition Code

**apps/contacts/models.py:152-181** (`update_giving_stats()`)
- Aggregates donations with `donations.aggregate(...)`
- Sets 6 fields on self
- Calls `self.save(update_fields=[...])`
- **No locking, no F() expressions**
- Called from signal: `apps/donations/signals.py:17`

**apps/pledges/models.py:191-198** (`record_fulfillment()`)
- Uses `self.total_received += donation.amount` (read-modify-write)
- Calls `self.save()`
- **No locking, no F() expressions**
- Called from signal: `apps/donations/signals.py:26`

**apps/donations/signals.py:10-27** (`update_contact_stats_on_save`)
- Runs on every `Donation` post_save
- Calls `contact.update_giving_stats()` (line 17)
- Calls `contact.save(update_fields=['needs_thank_you'])` (line 22) — second save!
- Calls `pledge.record_fulfillment()` (line 26)
- **No signal disabling mechanism for bulk imports**

### What Exists in Journal Models

**apps/journals/models.py:**

**PipelineStage (lines 14-22):**
```python
class PipelineStage(models.TextChoices):
    CONTACT = 'contact', 'Contact'
    MEET = 'meet', 'Meet'
    CLOSE = 'close', 'Close'
    DECISION = 'decision', 'Decision'
    THANK = 'thank', 'Thank'
    NEXT_STEPS = 'next_steps', 'Next Steps'
```

**JournalStageEvent (lines 152-214):**
- FK to `journal_contact` (indexed)
- `stage` CharField with PipelineStage choices (indexed)
- `event_type` CharField (indexed)
- `created_at` timestamp (inherited from TimeStampedModel)
- **Indexes:**
  - `journal_contact, stage, created_at` (composite, line 208)
  - `journal_contact, created_at` (composite, line 209)

**Observation:** Indexes support efficient Subquery queries for "last event per contact" pattern.

**JournalContact (lines 120-150):**
- Through-table linking journals to contacts
- FK to `journal` (indexed)
- FK to `contact` (indexed)
- Unique constraint on `journal, contact`

**Decision (lines 232-292):**
- FK to `journal_contact` (indexed)
- Unique constraint per `journal_contact`
- Has `monthly_equivalent` property using Decimal (correct pattern, unlike Pledge)

### What Exists in User Model

**apps/users/models.py:**

**User model (lines 23-136):**
- `email` (unique)
- `role` CharField with UserRole choices: 'staff', 'admin', 'finance', 'read_only'
- `is_staff` BooleanField (Django builtin for admin site)
- `is_active` BooleanField
- Properties: `is_admin`, `is_finance`, `is_staff_role`, `is_read_only`

**Observation:** `is_staff` is separate from `role`. Most code uses `role == 'admin'`, not `is_staff`.

### What Indexes Exist on JournalStageEvent

From apps/journals/models.py:206-210:
```python
indexes = [
    models.Index(fields=['journal_contact', 'stage', 'created_at']),
    models.Index(fields=['journal_contact', 'created_at']),
]
```

**Analysis:** These indexes support:
1. Finding latest event per journal_contact (used in Subquery pattern)
2. Filtering events by stage within a journal_contact
3. Ordering by created_at for latest event queries

**For stalled contact detection:** Query pattern `JournalStageEvent.objects.filter(journal_contact__contact=OuterRef('pk')).order_by('-created_at')[:1]` will use the `journal_contact, created_at` index via reverse FK lookup.

### What Existing Admin Endpoint Patterns Look Like

**Pattern 1: Manual role check in view method** (existing, suboptimal)
```python
# apps/insights/views.py:114-117
def get(self, request):
    if request.user.role != 'admin':
        return Response({'detail': 'Admin access required'}, status=403)
    return Response(get_review_queue(request.user))
```

**Pattern 2: Manual multi-role check in view method** (existing, suboptimal)
```python
# apps/insights/views.py:138-140
def get(self, request):
    if request.user.role not in ['admin', 'finance']:
        return Response({'detail': 'Admin or finance access required'}, status=403)
    # ... rest of view
```

**Pattern 3: is_staff check** (existing, WRONG)
```python
# apps/journals/views.py:536
if not request.user.is_staff:
    return Response({'detail': 'Admin access required'}, status=403)
```

**Recommendation for Phase 13:** Use permission classes, not manual checks.

## Open Questions

Things that couldn't be fully resolved:

1. **Should existing ReviewQueueView and TransactionsView be refactored?**
   - What we know: They use manual role checks, not permission classes
   - What's unclear: Whether Phase 13 scope includes refactoring existing endpoints or just adding new ones
   - Recommendation: Refactor as part of "fix permission vulnerabilities" requirement — consistent pattern is security improvement

2. **Should finance/read_only roles see admin analytics?**
   - What we know: Requirements specify "ADMIN role-based access" — non-admin users receive 403
   - What's unclear: Whether "admin" means literally `role == 'admin'` or "admin-level users" (admin + finance)
   - Recommendation: Use `IsAdmin` permission class (admin only) per strict interpretation of requirements. Can easily change to `IsFinanceOrAdmin` if needed.

3. **Should signals be disabled during bulk import in Phase 13?**
   - What we know: Race condition exists in `update_giving_stats()` called from signals
   - What's unclear: Whether fixing the signal disabling is in scope for Phase 13 or separate refactor
   - Recommendation: Document as known issue, fix `record_fulfillment()` race (which is in requirements), defer signal refactor to separate phase

## Sources

### Primary (HIGH confidence)

**Codebase files read directly:**
- `/home/matkukla/projects/DonorCRM/apps/insights/views.py` — 7 existing analytics endpoints
- `/home/matkukla/projects/DonorCRM/apps/insights/services.py` — 9 service functions with aggregation patterns
- `/home/matkukla/projects/DonorCRM/apps/insights/urls.py` — URL registration pattern
- `/home/matkukla/projects/DonorCRM/apps/core/permissions.py` — 6 permission classes including IsAdmin
- `/home/matkukla/projects/DonorCRM/apps/contacts/models.py` — update_giving_stats() race condition (lines 152-181)
- `/home/matkukla/projects/DonorCRM/apps/pledges/models.py` — record_fulfillment() race condition (lines 191-198), monthly_equivalent float issue (lines 137-146)
- `/home/matkukla/projects/DonorCRM/apps/journals/models.py` — PipelineStage, JournalStageEvent, JournalContact, Decision models with indexes
- `/home/matkukla/projects/DonorCRM/apps/journals/views.py` — JournalAnalyticsViewSet with Subquery pattern (lines 483-495), admin_summary is_staff issue (line 536)
- `/home/matkukla/projects/DonorCRM/apps/users/models.py` — User model with role field
- `/home/matkukla/projects/DonorCRM/apps/donations/signals.py` — post_save signal that triggers race conditions
- `/home/matkukla/projects/DonorCRM/apps/contacts/views.py` — ListAPIView permission bypass examples
- `/home/matkukla/projects/DonorCRM/.planning/EDGE_CASE_AUDIT.md` — Comprehensive audit of 10 critical issues

### Secondary (MEDIUM confidence)

**Planning documents:**
- `.planning/research/ARCHITECTURE.md` — System architecture documentation
- `.planning/research/ADMIN_ANALYTICS_PITFALLS.md` — Known permission vulnerabilities
- `.planning/research/SUMMARY.md` — Research summary with existing patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries already in use, verified in codebase
- Architecture: HIGH — Patterns verified in 12+ existing endpoints
- Pitfalls: HIGH — All 5 pitfalls verified in Edge Case Audit with file/line references

**Research date:** 2026-02-12
**Valid until:** 2026-03-12 (30 days - codebase is stable, Django/DRF patterns are established)

**Query count achieved in existing endpoints:**
- `get_donations_by_month()`: 1 aggregate query
- `pipeline_breakdown()`: 1 query with Subquery annotation
- `admin_summary()`: 2 queries (journals count + aggregation)

**Target for Phase 13:** <20 queries per endpoint (requirement API-03) — achievable with existing patterns.
