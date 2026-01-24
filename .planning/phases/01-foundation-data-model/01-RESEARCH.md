# Phase 1: Foundation & Data Model - Research

**Researched:** 2026-01-24
**Domain:** Django REST Framework + PostgreSQL backend development
**Confidence:** HIGH

## Summary

This phase builds a new "journals" app following the existing DonorCRM Django/DRF patterns. The codebase has well-established conventions for models (TimeStampedModel base), permissions (IsContactOwnerOrReadAccess pattern), views (DRF generic views), and event logging (signals + services).

The research examined contacts, pledges, donations, events, and tasks apps to understand the architectural patterns. All apps follow a consistent structure: models inherit from TimeStampedModel (UUID primary key, timestamps), use Django signals for event creation, employ DRF generic views with permission classes, and register URLs through config/api_urls.py.

**Primary recommendation:** Follow the pledges app structure closely - it has money fields (DecimalField), owner-scoped queries, signals for event logging, and state management patterns (active/paused/cancelled status) that map well to journal requirements.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.11 | Web framework | Project standard, LTS version |
| Django REST Framework | latest | API framework | All endpoints use DRF generic views |
| PostgreSQL | default | Database | Configured in settings, supports UUIDs natively |
| Python | 3.12.3 | Language | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | latest | Queryset filtering | All list views use DjangoFilterBackend |
| drf-spectacular | latest | OpenAPI schema | All views should have @extend_schema decorators |
| python-decouple | latest | Configuration | Environment variables in settings |
| python-dateutil | latest | Date calculations | For relative date math (pledges use relativedelta) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DecimalField | IntegerField (cents) | DecimalField used throughout codebase (donations, pledges) - stick with it for consistency |
| Soft delete | Hard delete | No soft delete pattern exists in codebase - use is_archived boolean instead |
| JSONField | Separate tables | JSONField appropriate for metadata, but stage events need queryable fields |

**Installation:**
Not applicable - all dependencies already in project.

## Architecture Patterns

### Recommended Project Structure
```
apps/journals/
├── migrations/          # Django migrations
│   └── __init__.py
├── tests/              # Test files
│   ├── __init__.py
│   ├── factories.py    # Factory Boy factories
│   ├── test_models.py
│   └── test_views.py
├── __init__.py
├── apps.py             # App config with signals registration
├── models.py           # Journal, JournalContact, JournalStageEvent, JournalNextStep
├── serializers.py      # DRF serializers (list, detail, create)
├── views.py            # DRF generic views
├── urls.py             # URL patterns with app_name
├── signals.py          # Event creation signals
└── admin.py            # Django admin registration
```

### Pattern 1: TimeStampedModel Base Class
**What:** All models inherit from `apps.core.models.TimeStampedModel`
**When to use:** Every model in the journals app
**Example:**
```python
# Source: apps/contacts/models.py
from apps.core.models import TimeStampedModel

class Journal(TimeStampedModel):
    """
    Fundraising journal for tracking donor engagement pipeline.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='journals',
        db_index=True
    )
    # TimeStampedModel provides: id (UUID), created_at, updated_at
```

**Fields provided:**
- `id` = UUIDField (primary key, auto-generated)
- `created_at` = DateTimeField (auto_now_add=True, indexed)
- `updated_at` = DateTimeField (auto_now=True)
- Meta ordering = ['-created_at']

### Pattern 2: Owner-Scoped Permissions
**What:** Use `IsContactOwnerOrReadAccess` or create similar `IsJournalOwnerOrAdmin`
**When to use:** All journal detail/update/delete views
**Example:**
```python
# Source: apps/core/permissions.py (lines 65-98)
class IsContactOwnerOrReadAccess(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Admin has full access
        if request.user.role == 'admin':
            return True
        # Owner has full access
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        # Finance/read_only can only read
        if request.user.role in ['finance', 'read_only']:
            return request.method in permissions.SAFE_METHODS
        return False
```

**Key insight:**
- Permission classes check object-level ownership via `owner` field
- Admin gets full access
- Finance/read_only get read-only access
- Staff users only see their own objects

### Pattern 3: Queryset Scoping in Views
**What:** Filter querysets based on user role in `get_queryset()`
**When to use:** All list views
**Example:**
```python
# Source: apps/pledges/views.py (lines 29-44)
def get_queryset(self):
    user = self.request.user

    # Admin and Finance can see all
    if user.role in ['admin', 'finance', 'read_only']:
        queryset = Pledge.objects.all()
    else:
        # Staff sees only their contacts' pledges
        queryset = Pledge.objects.filter(contact__owner=user)

    return queryset.select_related('contact')
```

### Pattern 4: DRF Generic Views
**What:** Use DRF's generic views (ListCreateAPIView, RetrieveUpdateDestroyAPIView)
**When to use:** Standard CRUD operations
**Example:**
```python
# Source: apps/contacts/views.py (lines 39-76)
class ContactListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'created_at']
    filterset_fields = ['status', 'needs_thank_you']

    def get_queryset(self):
        # Scope by ownership

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ContactCreateSerializer
        return ContactListSerializer
```

### Pattern 5: Separate Serializers for List/Detail/Create
**What:** Use different serializers for different operations
**When to use:** When list needs fewer fields than detail, or create has different validation
**Example:**
```python
# Source: apps/contacts/serializers.py
# ContactListSerializer - minimal fields (lines 10-24)
# ContactDetailSerializer - all fields + read-only computed (lines 27-82)
# ContactCreateSerializer - auto-set owner from request (lines 85-120)

class ContactCreateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return Contact.objects.create(**validated_data)
```

### Pattern 6: Signal-Based Event Creation
**What:** Use Django signals to create events when models change
**When to use:** Audit trail, notifications, automatic event logging
**Example:**
```python
# Source: apps/pledges/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Pledge)
def handle_pledge_created(sender, instance, created, **kwargs):
    if created:
        Event.objects.create(
            user=instance.contact.owner,
            event_type=EventType.PLEDGE_CREATED,
            title=f'New pledge from {instance.contact.full_name}',
            severity=EventSeverity.SUCCESS,
            contact=instance.contact,
            metadata={'amount': str(instance.amount)}
        )
```

**Signal registration:**
```python
# Source: apps/pledges/apps.py
class PledgesConfig(AppConfig):
    name = 'apps.pledges'

    def ready(self):
        import apps.pledges.signals  # noqa: F401
```

### Pattern 7: TextChoices for Status Fields
**What:** Use Django's TextChoices for status enumerations
**When to use:** Any field with fixed set of values
**Example:**
```python
# Source: apps/pledges/models.py (lines 23-28)
class PledgeStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'

# Then in model:
status = models.CharField(
    'status',
    max_length=20,
    choices=PledgeStatus.choices,
    default=PledgeStatus.ACTIVE,
    db_index=True  # Always index status fields
)
```

### Pattern 8: Money Fields as DecimalField
**What:** Store money as DecimalField(max_digits=10, decimal_places=2)
**When to use:** All money amounts
**Example:**
```python
# Source: apps/pledges/models.py (lines 45-50)
amount = models.DecimalField(
    'amount',
    max_digits=10,
    decimal_places=2,
    validators=[MinValueValidator(Decimal('0.01'))],
    help_text='Committed amount per frequency period'
)
```

**Note:** Prior decision said "cents for money storage" but codebase uses DecimalField throughout. Follow codebase convention.

### Pattern 9: URL Registration
**What:** App defines `urls.py` with `app_name`, then included in `config/api_urls.py`
**When to use:** New app with API endpoints
**Example:**
```python
# Source: apps/pledges/urls.py
app_name = 'pledges'
urlpatterns = [
    path('', PledgeListCreateView.as_view(), name='pledge-list'),
    path('<uuid:pk>/', PledgeDetailView.as_view(), name='pledge-detail'),
]

# Source: config/api_urls.py (line 36)
path('pledges/', include('apps.pledges.urls')),
```

**Pattern:** `/api/v1/{app_name}/` prefix for all endpoints

### Pattern 10: Archive Pattern (Not Soft Delete)
**What:** No soft delete exists - use `is_archived` boolean if needed
**When to use:** When DELETE should hide, not destroy
**Example:**
```python
# Inferred from requirements (no existing pattern in codebase)
is_archived = models.BooleanField('archived', default=False, db_index=True)
archived_at = models.DateTimeField('archived at', null=True, blank=True)

def archive(self):
    """Archive the journal (soft delete)."""
    from django.utils import timezone
    self.is_archived = True
    self.archived_at = timezone.now()
    self.save(update_fields=['is_archived', 'archived_at'])
```

**Queryset scoping:**
```python
def get_queryset(self):
    # Exclude archived by default
    queryset = Journal.objects.filter(is_archived=False)
    # ... apply ownership scoping
    return queryset
```

### Anti-Patterns to Avoid

- **Don't use relative imports within app** - Use `from apps.journals.models import Journal` not `from .models import Journal` (codebase uses absolute)
- **Don't create owner in serializer validate()** - Do it in `create()` method (see ContactCreateSerializer line 108-111)
- **Don't forget select_related()** - Always use `.select_related('owner')` in querysets to avoid N+1 queries (see contacts/views.py line 71)
- **Don't forget db_index=True** - Index all foreign keys, status fields, and commonly queried booleans
- **Don't use generic Event.objects.create()** - Use `apps.events.services.create_event()` for consistency (though signals pattern also works)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination | Custom pagination logic | StandardPagination from apps.core.pagination | Already configured in REST_FRAMEWORK settings |
| Permission checking | Custom permission logic in views | DRF permission classes (IsContactOwnerOrReadAccess) | Handles edge cases, tested, reusable |
| Event logging | Manual Event creation in views | Django signals + Event.objects.create() | Decouples business logic from audit trail |
| Owner assignment | Require owner in POST body | Auto-assign from request.user in serializer | Security - users can't create for others |
| Filtering/Search | Manual queryset filtering | django-filter DjangoFilterBackend | Already configured, handles query params |
| OpenAPI docs | Manual schema writing | @extend_schema decorators from drf-spectacular | Auto-generates docs, keeps them current |
| UUID generation | Manual uuid.uuid4() | TimeStampedModel base class | Already provides UUID primary key |
| Timestamps | Manual timezone.now() | TimeStampedModel base class | Auto-managed created_at/updated_at |

**Key insight:** The codebase has mature patterns for almost everything needed. Don't reinvent - follow existing apps' structure.

## Common Pitfalls

### Pitfall 1: Forgetting to Register Signals
**What goes wrong:** Signals don't fire, events aren't created
**Why it happens:** Signals module imported but not registered in apps.py
**How to avoid:**
```python
# apps/journals/apps.py
class JournalsConfig(AppConfig):
    name = 'apps.journals'

    def ready(self):
        import apps.journals.signals  # noqa: F401
```
**Warning signs:** No events appearing in database after creating/updating journals

### Pitfall 2: Circular Import in Signals
**What goes wrong:** ImportError when Django loads
**Why it happens:** Importing models at module level in signals.py
**How to avoid:** Import inside signal handler function
```python
# BAD
from apps.events.models import Event

@receiver(post_save, sender=Journal)
def handle_journal_created(sender, instance, created, **kwargs):
    Event.objects.create(...)

# GOOD
@receiver(post_save, sender=Journal)
def handle_journal_created(sender, instance, created, **kwargs):
    from apps.events.models import Event
    Event.objects.create(...)
```
**Warning signs:** Django startup fails with circular import error

### Pitfall 3: Not Scoping Querysets by Ownership
**What goes wrong:** Users see other users' data
**Why it happens:** Forgot to filter by owner in get_queryset()
**How to avoid:** Always filter based on user.role and owner field
```python
def get_queryset(self):
    user = self.request.user
    if user.role in ['admin', 'finance', 'read_only']:
        return Journal.objects.all()
    return Journal.objects.filter(owner=user)
```
**Warning signs:** Test as staff user, see admin's data

### Pitfall 4: Missing db_index on Foreign Keys and Status
**What goes wrong:** Slow queries on large datasets
**Why it happens:** Django doesn't auto-index all foreign keys (it does for some, but be explicit)
**How to avoid:** Always add `db_index=True` to:
- Foreign keys (owner, contact, journal)
- Status/boolean fields used in filtering
- Date fields used in ordering/filtering
**Warning signs:** Slow API responses as data grows

### Pitfall 5: DecimalField Serialization Issues
**What goes wrong:** JSON serialization errors or precision loss
**Why it happens:** Decimal objects need explicit conversion
**How to avoid:** Let DRF handle it automatically, or use SerializerMethodField for custom formatting
```python
# DRF auto-handles DecimalField -> JSON
class Meta:
    fields = ['amount']  # DecimalField serializes fine

# If custom formatting needed
monthly_equivalent = serializers.SerializerMethodField()

def get_monthly_equivalent(self, obj):
    return f'{obj.monthly_equivalent:.2f}'
```
**Warning signs:** "Object of type Decimal is not JSON serializable"

### Pitfall 6: Forgetting INSTALLED_APPS Registration
**What goes wrong:** Django can't find models, migrations don't run
**Why it happens:** New app not added to settings.LOCAL_APPS
**How to avoid:** Add to config/settings/base.py:
```python
LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.contacts',
    'apps.journals',  # ADD THIS
    # ...
]
```
**Warning signs:** "No module named apps.journals" or migrations not detected

### Pitfall 7: Missing URL Registration
**What goes wrong:** 404 on all journal endpoints
**Why it happens:** Forgot to include journals.urls in config/api_urls.py
**How to avoid:** Add to config/api_urls.py urlpatterns:
```python
path('journals/', include('apps.journals.urls')),
```
**Warning signs:** GET /api/v1/journals/ returns 404

### Pitfall 8: Wrong Owner Field in Through Table
**What goes wrong:** Journal-Contact associations not owner-scoped correctly
**Why it happens:** Through table needs owner field for filtering, not just foreign keys
**How to avoid:** For JournalContact through table:
```python
class JournalContact(TimeStampedModel):
    journal = models.ForeignKey('Journal', on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    # DON'T add owner here - get it via journal.owner or contact.owner
```
**Warning signs:** Complex queries to check ownership in permissions

## Code Examples

Verified patterns from official sources:

### Creating a Model with TimeStampedModel
```python
# Source: apps/pledges/models.py (lines 31-66)
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal

from apps.core.models import TimeStampedModel

class Journal(TimeStampedModel):
    """Fundraising journal for tracking donor pipeline."""

    # Owner (staff member who owns this journal)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='journals',
        db_index=True
    )

    # Journal details
    name = models.CharField('name', max_length=255)
    goal_amount = models.DecimalField(
        'goal amount',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    deadline = models.DateField('deadline', null=True, blank=True)

    # Archive pattern
    is_archived = models.BooleanField('archived', default=False, db_index=True)
    archived_at = models.DateTimeField('archived at', null=True, blank=True)

    class Meta:
        db_table = 'journals'
        verbose_name = 'journal'
        verbose_name_plural = 'journals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_archived']),
        ]
```

### DRF Generic View with Ownership Scoping
```python
# Source: apps/pledges/views.py (lines 18-49)
from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class JournalListCreateView(generics.ListCreateAPIView):
    """
    GET: List journals (owner-scoped)
    POST: Create a new journal
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'deadline']
    ordering = ['-created_at']
    filterset_fields = ['is_archived']

    def get_queryset(self):
        user = self.request.user

        # Admin sees all journals
        if user.role == 'admin':
            queryset = Journal.objects.all()
        else:
            # Staff sees only their own journals
            queryset = Journal.objects.filter(owner=user)

        # Exclude archived by default unless filter applied
        if not self.request.query_params.get('is_archived'):
            queryset = queryset.filter(is_archived=False)

        return queryset.select_related('owner')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JournalCreateSerializer
        return JournalListSerializer
```

### Serializer with Auto-Owner Assignment
```python
# Source: apps/contacts/serializers.py (lines 105-120)
class JournalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = ['id', 'name', 'goal_amount', 'deadline']
        read_only_fields = ['id']

    def create(self, validated_data):
        # Auto-assign owner from request user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user

        return Journal.objects.create(**validated_data)
```

### Signal for Event Creation
```python
# Source: apps/pledges/signals.py (lines 23-42)
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.journals.models import Journal

@receiver(post_save, sender=Journal)
def handle_journal_created(sender, instance, created, **kwargs):
    """Create event when journal is created."""
    if created:
        from apps.events.models import Event, EventType, EventSeverity

        Event.objects.create(
            user=instance.owner,
            event_type=EventType.CONTACT_CREATED,  # Would need new JOURNAL_CREATED
            title=f'Journal created: {instance.name}',
            message=f'Goal: ${instance.goal_amount}',
            severity=EventSeverity.INFO,
            metadata={
                'journal_id': str(instance.id),
                'goal_amount': str(instance.goal_amount),
            }
        )
```

### URL Patterns with app_name
```python
# Source: apps/pledges/urls.py
from django.urls import path
from apps.journals.views import (
    JournalListCreateView,
    JournalDetailView,
)

app_name = 'journals'

urlpatterns = [
    path('', JournalListCreateView.as_view(), name='journal-list'),
    path('<uuid:pk>/', JournalDetailView.as_view(), name='journal-detail'),
]
```

### ManyToMany Through Table
```python
# Source: Inferred from contacts.groups ManyToMany pattern
class JournalContact(TimeStampedModel):
    """
    Many-to-many relationship between journals and contacts.
    Tracks which contacts are in which journals.
    """
    journal = models.ForeignKey(
        'Journal',
        on_delete=models.CASCADE,
        related_name='journal_contacts',
        db_index=True
    )
    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='journal_memberships',
        db_index=True
    )

    class Meta:
        db_table = 'journal_contacts'
        unique_together = [['journal', 'contact']]
        indexes = [
            models.Index(fields=['journal', 'contact']),
        ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| IntegerField for money (cents) | DecimalField with decimal_places=2 | Pre-project | All money fields use DecimalField (donations, pledges) |
| Manual event creation | Django signals + Event model | Project architecture | Automatic audit trail |
| Permission in view logic | DRF permission classes | DRF best practice | Reusable, testable |
| Generic foreign keys everywhere | Direct foreign keys + optional GenericFK | Performance | Events use GenericFK, but also have direct contact FK for queries |

**Deprecated/outdated:**
- N/A - Project is current (Django 4.2.11 LTS, DRF latest)

## Open Questions

Things that couldn't be fully resolved:

1. **Stage Event Types**
   - What we know: Events app has EventType enum, signals create events
   - What's unclear: Should we add new EventType values for journal stages, or use metadata field?
   - Recommendation: Add new EventType values (JOURNAL_CONTACT_LOGGED, JOURNAL_MEETING, etc.) following existing pattern

2. **Next Steps vs Tasks**
   - What we know: Tasks app exists with Task model
   - What's unclear: Should JournalNextStep be a separate model or just use Task model with journal FK?
   - Recommendation: Use existing Task model, add optional journal FK to Task model (follow Contact->Task pattern)

3. **Money Field Storage**
   - What we know: Codebase uses DecimalField everywhere
   - What's unclear: Prior decision said "cents for storage" but code doesn't match
   - Recommendation: Follow codebase convention - use DecimalField(max_digits=10, decimal_places=2)

4. **Archive vs Delete**
   - What we know: No soft delete pattern exists in codebase
   - What's unclear: DELETE endpoint should soft-delete (archive) or hard-delete?
   - Recommendation: Implement is_archived pattern for journals, use DELETE to set is_archived=True

## Sources

### Primary (HIGH confidence)
- /home/matkukla/projects/DonorCRM/apps/core/models.py - TimeStampedModel base class
- /home/matkukla/projects/DonorCRM/apps/core/permissions.py - Permission classes
- /home/matkukla/projects/DonorCRM/apps/contacts/models.py - Owner-scoped model pattern
- /home/matkukla/projects/DonorCRM/apps/contacts/views.py - DRF generic view patterns
- /home/matkukla/projects/DonorCRM/apps/contacts/serializers.py - Serializer patterns (list/detail/create)
- /home/matkukla/projects/DonorCRM/apps/pledges/models.py - Money field pattern, status enums
- /home/matkukla/projects/DonorCRM/apps/pledges/views.py - Ownership scoping in views
- /home/matkukla/projects/DonorCRM/apps/pledges/signals.py - Signal pattern for events
- /home/matkukla/projects/DonorCRM/apps/pledges/apps.py - Signal registration in AppConfig
- /home/matkukla/projects/DonorCRM/apps/events/models.py - Event model and types
- /home/matkukla/projects/DonorCRM/apps/tasks/models.py - Task model structure
- /home/matkukla/projects/DonorCRM/config/settings/base.py - INSTALLED_APPS registration
- /home/matkukla/projects/DonorCRM/config/api_urls.py - URL registration pattern

### Secondary (MEDIUM confidence)
- N/A - All findings from direct codebase inspection

### Tertiary (LOW confidence)
- Archive pattern inferred from requirements (no existing implementation in codebase)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified in codebase
- Architecture: HIGH - All patterns observed in multiple apps
- Pitfalls: HIGH - Common Django/DRF issues, verified against codebase patterns
- Stage events: MEDIUM - Need to extend EventType enum (not yet confirmed approach)
- Archive pattern: MEDIUM - Inferred from requirements, no existing implementation

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - Django/DRF stable, codebase patterns unlikely to change)
