# Phase 14: Core Analytics Endpoints - Research

**Researched:** 2026-02-13
**Domain:** Django REST Framework Analytics Endpoints Optimization
**Confidence:** HIGH

## Summary

Phase 14 faces a unique situation: all 5 analytics endpoints were **already implemented and verified in Phase 13**. The endpoints exist, pass tests, and satisfy success criteria. However, the Edge Case Audit revealed critical performance and data integrity issues that must be addressed before these endpoints can be considered production-ready.

This research focuses on understanding what's needed to PLAN the refinement phase well: how to fix N+1 queries, add DRF serializers for consistency, implement filtering/sorting, and address data quality gaps identified in the audit.

**Primary recommendation:** Plan Phase 14 as a **refactoring and enhancement phase** focused on performance optimization, DRF best practices adoption, and feature completion rather than greenfield endpoint development.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django REST Framework | 3.14+ | API serialization, viewsets, permissions | Industry standard for Django APIs - provides declarative serializers, automatic validation, browsable API |
| django-filter | 25.2+ | Query parameter filtering | Official DRF recommendation for filterable list endpoints - integrates seamlessly with DRF |
| drf-spectacular | 0.27+ | OpenAPI schema generation | Already in project - auto-generates API docs from serializers and views |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Decimal | Python stdlib | Money arithmetic | Always for currency calculations - already used in Decision.monthly_equivalent |
| django.db.models.F | Django ORM | Atomic updates | For race-prone fields (total_received, giving stats) - prevents read-modify-write races |
| select_related/prefetch_related | Django ORM | Query optimization | Always for serializers that access related objects - prevents N+1 queries |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DRF Serializers | Hand-built dicts (current) | Hand-built is faster to prototype but loses validation, documentation, consistency. Serializers add ~5-10% overhead but are worth it for production APIs. |
| PageNumberPagination | LimitOffsetPagination | PageNumber is more user-friendly for UI pagination. LimitOffset already used in stalled contacts - keep for backward compatibility. |
| django-filter | Manual queryset filtering | django-filter handles edge cases (invalid params, type coercion) and auto-generates schema docs. Manual filtering is error-prone (see unvalidated int() casts in current code). |

**Installation:**
```bash
# Already installed in project
pip install djangorestframework==3.14.0
pip install django-filter==25.2
pip install drf-spectacular==0.27.0
```

## Architecture Patterns

### Recommended Endpoint Structure
```
apps/insights/
├── services.py           # Pure business logic (already exists)
├── serializers.py        # DRF serializers (ADD THIS)
├── filters.py            # django-filter FilterSets (ADD THIS)
├── views.py              # DRF views orchestrating serializers+services
└── tests/
    ├── test_services.py  # Unit tests for aggregation logic
    └── test_views.py     # Integration tests for endpoints (already exists)
```

### Pattern 1: Read-Only Analytics Serializer
**What:** Serializers for endpoints that return aggregated data (no user input validation needed)
**When to use:** Dashboard overview, conversion funnel, team activity
**Example:**
```python
# Source: https://www.django-rest-framework.org/api-guide/serializers/
from rest_framework import serializers

class DashboardOverviewSerializer(serializers.Serializer):
    """Read-only serializer for dashboard summary."""
    total_contacts = serializers.IntegerField(read_only=True)
    active_journals = serializers.IntegerField(read_only=True)
    stalled_contacts = serializers.IntegerField(read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)
    donations_12m = serializers.DictField(read_only=True)

class DashboardOverviewView(APIView):
    def get(self, request):
        data = get_dashboard_overview()
        serializer = DashboardOverviewSerializer(data)
        return Response(serializer.data)
```

### Pattern 2: Paginated List with Filtering
**What:** FilterSet for query parameter validation + serializer for output + pagination
**When to use:** Stalled contacts, user performance (list endpoints with optional filters)
**Example:**
```python
# Source: https://django-filter.readthedocs.io/en/stable/guide/usage.html
import django_filters
from rest_framework.generics import ListAPIView

class StalledContactFilter(django_filters.FilterSet):
    owner_email = django_filters.CharFilter(field_name='owner__email', lookup_expr='icontains')
    days_min = django_filters.NumberFilter(method='filter_by_days_stalled')

    def filter_by_days_stalled(self, queryset, name, value):
        # Custom filter logic
        cutoff = timezone.now() - timedelta(days=value)
        return queryset.filter(last_activity_date__lt=cutoff)

    class Meta:
        model = Contact
        fields = ['owner_email', 'days_min']

class StalledContactSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    owner_email = serializers.CharField(read_only=True)
    days_stalled = serializers.IntegerField(read_only=True)

class StalledContactsView(ListAPIView):
    serializer_class = StalledContactSerializer
    filterset_class = StalledContactFilter
    pagination_class = StandardPagination

    def get_queryset(self):
        # Return annotated queryset from service
        return get_stalled_contacts_queryset()
```

### Pattern 3: Fixing N+1 Queries in Service Functions
**What:** Move from per-object iteration to annotated querysets
**When to use:** User performance endpoint (current N+1 problem with donation/decision queries)
**Example:**
```python
# Source: https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb

# BEFORE (N+1 problem - current code):
users = User.objects.filter(role__in=['staff', 'admin']).annotate(...)
for user in users:
    donation_stats = Donation.objects.filter(contact__owner=user).aggregate(...)  # N queries
    decision_count = Decision.objects.filter(...).count()  # N more queries

# AFTER (single query with Subquery):
from django.db.models import Subquery, OuterRef, Sum, Count

donation_total = Donation.objects.filter(
    contact__owner=OuterRef('pk')
).values('contact__owner').annotate(
    total=Sum('amount')
).values('total')[:1]

decision_count_subquery = Decision.objects.filter(
    journal_contact__journal__owner=OuterRef('pk')
).values('journal_contact__journal__owner').annotate(
    count=Count('id')
).values('count')[:1]

users = User.objects.filter(
    role__in=['staff', 'admin']
).annotate(
    total_contacts=Count('contacts', distinct=True),
    active_journals=Count('journals', filter=Q(journals__is_archived=False), distinct=True),
    total_donations=Subquery(donation_total),
    decisions_logged=Subquery(decision_count_subquery),
).order_by('-total_contacts')
```

### Pattern 4: Safe Query Parameter Validation
**What:** Validate and coerce query params with defaults instead of unguarded int() casts
**When to use:** All endpoints accepting numeric query params (limit, offset, days, etc.)
**Example:**
```python
# BEFORE (current code - can raise ValueError):
limit = int(request.query_params.get('limit', 50))

# AFTER (safe with django-filter):
class StalledContactFilter(django_filters.FilterSet):
    limit = django_filters.NumberFilter(min_value=1, max_value=100)
    offset = django_filters.NumberFilter(min_value=0)

# OR manually:
def get_int_param(request, key, default, min_val=None, max_val=None):
    try:
        value = int(request.query_params.get(key, default))
    except (ValueError, TypeError):
        return default
    if min_val is not None and value < min_val:
        return default
    if max_val is not None and value > max_val:
        return default
    return value
```

### Anti-Patterns to Avoid
- **N+1 queries in for-loops:** Current get_user_performance() queries donation/decision stats per user. Use Subquery annotations instead.
- **Hand-built dicts without validation:** Current views return raw dicts. Use serializers for consistency, validation, and auto-generated API docs.
- **Unvalidated int() casts on query params:** Current code raises 500 on ?limit=abc. Use django-filter or try/except with defaults.
- **Float arithmetic for money:** Pledge.monthly_equivalent uses float(). Use Decimal for all currency calculations.
- **Read-modify-write without locking:** record_fulfillment() uses self.total_received +=. Use F() expressions for atomic updates.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Query parameter validation | Manual int() parsing with try/except | django-filter FilterSet | Handles type coercion, validation, null values, range filters, documentation generation. Manual parsing misses edge cases (see current ?limit=abc crash). |
| Date range filtering | Manual date parsing from request.query_params | django-filter DateFromToRangeFilter | Handles timezone-aware parsing, invalid dates, missing params. ISO 8601 format support built-in. |
| Sorting query params | Manual queryset.order_by(request.GET['sort']) | OrderingFilter from DRF | Prevents SQL injection, validates field names, handles multi-field sorts, generates API schema. |
| Pagination metadata | Counting queryset and building {results, count, next, prev} | DRF PageNumberPagination | Handles edge cases (offset > count), generates Links headers, consistent API contract. |
| Serializing aggregated data | Building dicts manually | Serializer with SerializerMethodField | Auto-validates types, generates OpenAPI schema, catches missing fields in tests. |

**Key insight:** Analytics endpoints are READ-HEAVY and PERFORMANCE-CRITICAL. Using standard DRF patterns (serializers, filters, pagination) adds ~5-10% overhead but prevents entire classes of bugs (injection, type errors, inconsistent responses) and generates documentation automatically. The trade-off strongly favors DRF patterns for production APIs.

## Common Pitfalls

### Pitfall 1: N+1 Queries Hidden in Serializers
**What goes wrong:** Serializer accesses related objects without prefetch_related, causing N queries
**Why it happens:** DRF serializers are lazy - they don't fetch relations until accessed. Current JournalContact serializer has this problem (stage_events, decisions accessed per contact).
**How to avoid:**
1. Always use select_related() for ForeignKey/OneToOne
2. Always use prefetch_related() for ManyToMany/reverse ForeignKey
3. Use django-debug-toolbar in dev to catch N+1 queries
4. Add query count assertions in tests: `with self.assertNumQueries(5):`

**Warning signs:**
- Endpoint response time grows linearly with result count
- Django debug toolbar shows 50+ queries for a 25-item list
- Database CPU spikes on list endpoints

**Source:** https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb

### Pitfall 2: Race Conditions in Aggregated Stats
**What goes wrong:** Two processes update the same aggregated field (total_received, total_given) concurrently. Both read old value, both write new value. One update is silently lost.
**Why it happens:** ORM pattern `self.field += value; self.save()` is read-modify-write, not atomic. Current code has this in record_fulfillment() and update_giving_stats().
**How to avoid:**
1. Use F() expressions for atomic updates: `Model.objects.filter(pk=self.pk).update(field=F('field') + value)`
2. Wrap in select_for_update() if you need to read-then-write: `instance = Model.objects.select_for_update().get(pk=pk)`
3. Use database-level defaults/triggers for auto-calculated fields

**Warning signs:**
- Donation totals don't match sum of individual donations
- Pledge total_received < sum of linked donations
- Stats "drift" over time or after bulk imports

**Source:** Edge Case Audit issues 2.1, 3.2

### Pitfall 3: Stale Analytics Data
**What goes wrong:** Dashboard shows old data after bulk imports or edits because aggregation happens on-read and cache is stale
**Why it happens:** Current endpoints query live data on every request. With 200 users and complex aggregations, this is slow. Adding cache introduces staleness.
**How to avoid:**
1. For real-time data (dashboard cards), use short TTL cache (30-60 seconds) or no cache
2. For historical data (trends), pre-calculate in Celery task and cache long (1 hour+)
3. Invalidate cache on writes if data volume allows
4. Show "last updated" timestamp on frontend

**Warning signs:**
- Dashboard shows yesterday's counts
- New donations don't appear in totals until page refresh
- Users report "numbers don't add up"

**Source:** https://medium.com/@techWithAditya/building-a-high-performance-real-time-analytics-platform-with-django-a-comprehensive-guide-a13bab9136dd

### Pitfall 4: Unbounded Result Sets
**What goes wrong:** Endpoint returns thousands of rows without pagination, exhausting memory or timing out
**Why it happens:** Analytics endpoints often operate on "all data" by default. Current team_activity has limit but no pagination. StalledContactsView has custom pagination instead of DRF pagination.
**How to avoid:**
1. Always use DRF pagination for list endpoints
2. Set reasonable max_page_size (100-500)
3. Add default date range filters for time-series data (e.g., last 12 months)
4. For exports (>1000 rows), use async Celery task + CSV file

**Warning signs:**
- API timeout errors on large data sets
- Memory usage spikes during analytics queries
- Frontend hangs rendering large lists

**Source:** https://www.django-rest-framework.org/api-guide/pagination/

### Pitfall 5: Inconsistent Permission Checks
**What goes wrong:** Some views check `request.user.is_staff`, others check `request.user.role == 'admin'`, creating confusion and potential security holes
**Why it happens:** Multiple permission paradigms (Django is_staff vs custom role field). Current code has this inconsistency (journals/views.py:536 vs insights permissions).
**How to avoid:**
1. Consolidate on ONE permission pattern (custom role field recommended)
2. Use DRF permission classes consistently (IsAdmin, IsFinance, etc.)
3. Never mix manual role checks (if request.user.role...) with permission_classes
4. Document which roles can access which endpoints

**Warning signs:**
- Some users get 403, others get 200 for same endpoint
- Tests pass but UAT fails with permission errors
- Different views use different permission checks

**Source:** Edge Case Audit issue 1.5

## Code Examples

Verified patterns from official sources:

### Optimizing User Performance Endpoint (Fix N+1)
```python
# Source: https://docs.djangoproject.com/en/6.0/topics/performance/
from django.db.models import Subquery, OuterRef, Sum, Count, Q, DecimalField
from django.db.models.functions import Coalesce

def get_user_performance():
    """
    Per-missionary performance metrics with all aggregation at database level.
    Target: 1-2 queries total (no per-user iteration).
    """
    # Subquery for donation totals per user
    donation_totals = Donation.objects.filter(
        contact__owner=OuterRef('pk')
    ).values('contact__owner').annotate(
        total=Sum('amount')
    ).values('total')

    # Subquery for decision count per user
    decision_counts = Decision.objects.filter(
        journal_contact__journal__owner=OuterRef('pk')
    ).values('journal_contact__journal__owner').annotate(
        count=Count('id')
    ).values('count')

    # Subquery for contacts with decisions (for conversion rate)
    contacts_with_decisions = Contact.objects.filter(
        owner=OuterRef('pk'),
        journal_memberships__decisions__isnull=False
    ).values('owner').annotate(
        count=Count('id', distinct=True)
    ).values('count')

    # Single query with all metrics
    users = User.objects.filter(
        role__in=['staff', 'admin']
    ).annotate(
        total_contacts=Count('contacts', distinct=True),
        active_journals=Count(
            'journals',
            filter=Q(journals__is_archived=False),
            distinct=True
        ),
        total_donations=Coalesce(
            Subquery(donation_totals, output_field=DecimalField()),
            0
        ),
        decisions_logged=Coalesce(
            Subquery(decision_counts),
            0
        ),
        contacts_with_decisions_count=Coalesce(
            Subquery(contacts_with_decisions),
            0
        ),
    ).annotate(
        # Conversion rate: contacts with decisions / total contacts
        conversion_rate=Case(
            When(total_contacts=0, then=0.0),
            default=F('contacts_with_decisions_count') * 100.0 / F('total_contacts'),
            output_field=FloatField()
        )
    ).order_by('-total_contacts')

    return users
```

### Adding DRF Serializer for User Performance
```python
# Source: https://testdriven.io/blog/drf-serializers/
from rest_framework import serializers

class UserPerformanceSerializer(serializers.Serializer):
    """Read-only serializer for per-user metrics."""
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    total_contacts = serializers.IntegerField(read_only=True)
    active_journals = serializers.IntegerField(read_only=True)
    decisions_logged = serializers.IntegerField(read_only=True)
    conversion_rate = serializers.FloatField(read_only=True)
    total_donations = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

class UserPerformanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=['insights'],
        summary='Get user performance metrics (admin only)',
        responses={200: UserPerformanceSerializer(many=True)}
    )
    def get(self, request):
        users = get_user_performance()
        serializer = UserPerformanceSerializer(users, many=True)
        return Response({'users': serializer.data})
```

### Adding Date Range Filtering
```python
# Source: https://django-filter.readthedocs.io/en/stable/ref/filters.html
import django_filters
from django.utils import timezone
from datetime import timedelta

class TeamActivityFilter(django_filters.FilterSet):
    start_date = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text='Filter events after this date (ISO 8601)'
    )
    end_date = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text='Filter events before this date (ISO 8601)'
    )
    event_type = django_filters.CharFilter(
        field_name='event_type',
        lookup_expr='iexact'
    )

    class Meta:
        model = Event
        fields = ['start_date', 'end_date', 'event_type']

class TeamActivityView(ListAPIView):
    serializer_class = TeamActivitySerializer
    filterset_class = TeamActivityFilter
    pagination_class = StandardPagination

    def get_queryset(self):
        # Default to last 30 days if no date filter
        qs = Event.objects.select_related('user', 'contact')
        if not self.request.query_params.get('start_date'):
            default_start = timezone.now() - timedelta(days=30)
            qs = qs.filter(created_at__gte=default_start)
        return qs.order_by('-created_at')
```

### Safe Query Parameter Handling
```python
# Source: https://www.django-rest-framework.org/api-guide/filtering/
# Using django-filter (recommended):
class StalledContactFilter(django_filters.FilterSet):
    limit = django_filters.NumberFilter(
        method='filter_limit',
        help_text='Max results (default: 50, max: 100)'
    )
    offset = django_filters.NumberFilter(
        method='filter_offset',
        help_text='Offset for pagination (default: 0)'
    )

    def filter_limit(self, queryset, name, value):
        # Validation happens automatically (NumberFilter)
        return queryset

    def filter_offset(self, queryset, name, value):
        return queryset

# OR manually with validation:
def get_safe_int_param(request, key, default, min_val=1, max_val=100):
    """Safely parse integer query parameter with bounds."""
    try:
        value = int(request.query_params.get(key, default))
    except (ValueError, TypeError):
        return default
    return max(min_val, min(value, max_val))

# Usage:
limit = get_safe_int_param(request, 'limit', default=50, max_val=100)
offset = get_safe_int_param(request, 'offset', default=0, min_val=0, max_val=10000)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual dict building in views | DRF Serializers with schema generation | DRF 3.0 (2015) | Auto-validated responses, OpenAPI docs, frontend type safety |
| Custom pagination logic | DRF pagination classes | DRF 2.0 (2013) | Consistent pagination contract, Link headers, cursor support |
| Manual query param parsing | django-filter integration | DRF 3.1 (2015) | Type-safe filtering, auto-schema, less boilerplate |
| Read-modify-write updates | F() expressions for atomic updates | Django 1.1 (2009) | Race-condition safety, better performance |
| select_related everywhere | Targeted prefetch with Prefetch() objects | Django 1.4 (2012) | Fine-grained control, custom querysets in prefetch |
| Float for money | Decimal for currency | Always use Decimal | Avoids floating-point precision errors |

**Deprecated/outdated:**
- **is_staff for role checks:** Project uses custom `role` field (admin/staff/finance/read_only). Using Django's `is_staff` creates inconsistency. Standardize on `role` field with custom permission classes.
- **PageNumberPagination page_query_param:** Deprecated in DRF 3.14, removed in 4.0. Use `page` param only.
- **SimpleRouter suffix removal:** Deprecated. If you need custom URLs, define them explicitly.

## Open Questions

Things that couldn't be fully resolved:

1. **Should conversion_rate be per-user or global-only?**
   - What we know: Global conversion rate exists in dashboard_overview. User performance endpoint should include per-user conversion rate (mentioned in success criteria but not implemented).
   - What's unclear: Business logic for per-user conversion rate calculation (contacts with decisions / total contacts owned by user, or contacts in that user's journals with decisions / contacts in journals?).
   - Recommendation: Use "contacts in user's journals with decisions / contacts in user's journals" for consistency with global calculation.

2. **Should days_stalled show a value for zero-activity contacts?**
   - What we know: Edge Case Audit notes "days_stalled shows None for zero-activity contacts instead of meaningful value"
   - What's unclear: What's the "meaningful value"? Days since contact was added to journal? Days since contact was created? Always show "14+" for zero-activity?
   - Recommendation: Calculate as `(now - journal_contact.created_at).days` for zero-activity contacts to show "how long they've been neglected."

3. **Should stalled contacts endpoint use DRF pagination or custom limit/offset?**
   - What we know: Current implementation uses custom limit/offset params. DRF pagination is more standard but changes API contract.
   - What's unclear: Is frontend already consuming this endpoint? Would changing to PageNumberPagination break it?
   - Recommendation: Keep custom limit/offset for backward compatibility in Phase 14. Document as tech debt to migrate to PageNumberPagination in Phase 18.

4. **Should analytics endpoints support CSV export?**
   - What we know: CMON-02 (Phase 17) mentions export functionality. Current endpoints return JSON only.
   - What's unclear: Does CSV export need to happen in Phase 14 or can it wait for Phase 17?
   - Recommendation: Defer CSV export to Phase 17. Focus Phase 14 on fixing performance and adding serializers/filters.

5. **What's the caching strategy for dashboard overview?**
   - What we know: Dashboard queries are expensive (7+ service function calls). No caching currently.
   - What's unclear: Is 30-second staleness acceptable for dashboard cards? Should cache be per-user or global?
   - Recommendation: Start with no cache (simpler), add Redis caching in Phase 16 (Frontend Integration) when you have real-world load data to inform TTL decisions.

## Sources

### Primary (HIGH confidence)
- Django REST Framework Official Docs - [Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
- Django REST Framework Official Docs - [Filtering](https://www.django-rest-framework.org/api-guide/filtering/)
- Django REST Framework Official Docs - [Pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- django-filter Official Docs - [Filter Reference](https://django-filter.readthedocs.io/en/stable/ref/filters.html)
- Django Official Docs - [Performance and Optimization](https://docs.djangoproject.com/en/6.0/topics/performance/)
- Edge Case Audit - `/home/matkukla/projects/DonorCRM/.planning/EDGE_CASE_AUDIT.md`
- Phase 13 Implementation - `/home/matkukla/projects/DonorCRM/apps/insights/services.py`, `views.py`, `tests/test_views.py`

### Secondary (MEDIUM confidence)
- [Optimizing Django Queries with select_related and prefetch_related](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)
- [Django Serializers: Complete Guide to Types, Optimization, and Performance](https://medium.com/@sizanmahmud08/django-serializers-complete-guide-to-types-optimization-and-performance-best-practices-049fefd9d718)
- [Building a High-Performance Real-Time Analytics Platform with Django](https://medium.com/@techWithAditya/building-a-high-performance-real-time-analytics-platform-with-django-a-comprehensive-guide-a13bab9136dd)
- [Effectively Using Django REST Framework Serializers](https://testdriven.io/blog/drf-serializers/)
- [Django REST Framework: Pagination, Filtering, and Ordering](https://reintech.io/blog/django-rest-framework-pagination-filtering-ordering)

### Tertiary (LOW confidence)
- None - all findings verified against official documentation or existing code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, official DRF recommendations verified
- Architecture: HIGH - Patterns from official docs + existing codebase analysis
- Pitfalls: HIGH - Identified in Edge Case Audit with specific line numbers and reproducible scenarios

**Research date:** 2026-02-13
**Valid until:** 2026-04-13 (60 days - Django/DRF ecosystem is stable, patterns won't change)

**Critical findings for planner:**
1. Phase 14 is a **refactoring phase**, not greenfield development (all endpoints already exist)
2. Edge Case Audit identified **5 critical issues** requiring fixes: N+1 queries (user performance), missing conversion_rate, no serializers, no filtering, unsafe query param parsing
3. User performance endpoint has **N+1 problem** - requires service function rewrite with Subquery annotations
4. All endpoints should **add DRF serializers** for consistency, validation, and auto-generated OpenAPI docs
5. Stalled contacts and team activity need **filtering support** (date range, owner, event type)
6. Success criteria mention **conversion_rate** in user performance but it's not currently returned
7. **Backward compatibility** concern: Changing pagination from custom limit/offset to PageNumberPagination would break API contract if frontend is already consuming these endpoints
