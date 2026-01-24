# Phase 2: Contact Membership & Search - Research

**Researched:** 2026-01-24
**Domain:** Django REST Framework many-to-many relationships, search/filtering APIs
**Confidence:** HIGH

## Summary

This phase adds API endpoints to the existing JournalContact through-table model (created in Phase 1) and implements search/filter functionality for contacts within a journal. The research focused on DRF best practices for many-to-many relationship APIs, query optimization patterns, and atomic transaction handling.

The standard approach uses DRF's generic views with the JournalContact through-table as the primary resource. For search/filter, DRF's built-in SearchFilter and DjangoFilterBackend provide robust, performant solutions when combined with proper queryset optimization (prefetch_related). The critical pitfall identified in the roadmap - atomic transaction scope bugs - requires wrapping create/delete operations in transaction.atomic() blocks to prevent race conditions and ensure data consistency.

Phase 1 already created the JournalContact model with unique_together constraint on (journal, contact). This phase exposes it via REST API endpoints and adds search capabilities that filter contacts within a journal context.

**Primary recommendation:** Use dedicated JournalContact ViewSets with nested URL routing (journals/{id}/members/), implement search via query parameters on journal detail endpoint, and wrap all membership changes in transaction.atomic() to prevent integrity errors.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.11 | Web framework | Project standard, LTS version |
| Django REST Framework | 3.14.0 | API framework | Already used in Phase 1 |
| django-filter | 23.5 | Queryset filtering | Already configured in project |
| PostgreSQL | default | Database | Supports atomic transactions, complex indexes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| N/A | N/A | No new libraries needed | Phase 1 stack covers all requirements |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Nested routes (/journals/{id}/contacts/) | Flat routes (/journal-members/) | Nested routes more RESTful but require extra URL config; flat is simpler and matches existing patterns |
| prefetch_related | Nested serializers with select_related | prefetch_related correct for many-to-many; select_related only works for ForeignKey/OneToOne |
| DRF built-in filters | Custom filtering logic | Built-in filters handle edge cases, provide consistent API, already configured |

**Installation:**
Not applicable - all dependencies already in project.

## Architecture Patterns

### Recommended Project Structure
```
apps/journals/
├── views.py            # Add JournalContactListCreateView, JournalContactDestroyView
├── serializers.py      # Add JournalContactSerializer, JournalContactDetailSerializer
├── urls.py             # Add journal-members endpoints
└── models.py           # Already has JournalContact (Phase 1)
```

### Pattern 1: Through-Table as Primary Resource
**What:** Expose JournalContact (the through-table) as the main API resource for membership operations
**When to use:** Many-to-many relationships where you need explicit add/remove operations
**Example:**
```python
# Source: DRF best practices for many-to-many through tables
# apps/journals/views.py

class JournalContactListCreateView(generics.ListCreateAPIView):
    """
    GET: List contacts in a journal (with search/filter)
    POST: Add contact to journal
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = JournalContactSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['contact__first_name', 'contact__last_name', 'contact__email']
    filterset_fields = ['contact__status']

    def get_queryset(self):
        # Filter by journal from URL or query param
        journal_id = self.request.query_params.get('journal_id')
        user = self.request.user

        # Base queryset with optimization
        queryset = JournalContact.objects.select_related(
            'journal', 'contact'
        )

        # Scope by ownership
        if user.role != 'admin':
            queryset = queryset.filter(journal__owner=user)

        # Filter by journal
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)

        return queryset
```

**Key insight:** Treating the through-table as a resource makes add/remove operations explicit and allows attaching metadata later (like date_added, added_by, etc.).

### Pattern 2: Atomic Transactions for Membership Changes
**What:** Wrap create/delete operations in transaction.atomic() to prevent race conditions
**When to use:** Any operation that modifies relationships and could have concurrent requests
**Example:**
```python
# Source: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
from django.db import transaction, IntegrityError

class JournalContactListCreateView(generics.ListCreateAPIView):
    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Validate and create membership
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED,
                    headers=headers
                )
        except IntegrityError:
            # Handle duplicate membership gracefully
            return Response(
                {'detail': 'Contact already in journal'},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**Why critical:** The roadmap specifically flags "Atomic transaction scope bugs" as a pitfall. Race conditions can occur when:
1. Multiple requests try to add the same contact simultaneously
2. Delete happens while a related update is in progress
3. Stage event creation fails after membership is created

### Pattern 3: Query Optimization with prefetch_related
**What:** Use prefetch_related for many-to-many relationships to avoid N+1 queries
**When to use:** Any queryset returning multiple JournalContact objects with related data
**Example:**
```python
# Source: Django ORM best practices
# Use select_related for journal (ForeignKey), prefetch for many-to-many if added later

def get_queryset(self):
    queryset = JournalContact.objects.select_related(
        'journal',      # ForeignKey - use select_related (SQL JOIN)
        'contact'       # ForeignKey - use select_related
    )

    # If contact has many-to-many groups:
    # queryset = queryset.prefetch_related('contact__groups')

    return queryset
```

**Performance impact:** Without select_related, fetching 100 journal contacts would execute:
- 1 query for JournalContact objects
- 100 queries for journals
- 100 queries for contacts
= **201 queries**

With select_related: **1 query** (SQL JOIN)

### Pattern 4: Search on Related Fields
**What:** Use double-underscore notation to search across relationships
**When to use:** Searching/filtering contacts within a journal
**Example:**
```python
# Source: https://www.django-rest-framework.org/api-guide/filtering/
class JournalContactListCreateView(generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]

    # Search across contact fields
    search_fields = [
        'contact__first_name',
        'contact__last_name',
        'contact__email'
    ]

    # Filter by contact status
    filterset_fields = ['contact__status']
```

**Usage:**
- `GET /api/v1/journal-members/?journal_id=<uuid>&search=john` - Search contacts named "john"
- `GET /api/v1/journal-members/?journal_id=<uuid>&contact__status=donor` - Filter by donor status

**Performance note:** SearchFilter uses case-insensitive `icontains` which can't use GIN indexes in PostgreSQL. For large datasets, consider custom search implementation.

### Pattern 5: Validation for unique_together
**What:** Let database constraints handle uniqueness, catch IntegrityError gracefully
**When to use:** Models with unique_together constraints
**Example:**
```python
# Source: https://www.django-rest-framework.org/api-guide/validators/
# JournalContact has unique_together on (journal, contact)

# OPTION 1: Database handles it, catch IntegrityError (RECOMMENDED)
def create(self, request, *args, **kwargs):
    try:
        with transaction.atomic():
            return super().create(request, *args, **kwargs)
    except IntegrityError:
        return Response(
            {'detail': 'Contact already in journal'},
            status=status.HTTP_400_BAD_REQUEST
        )

# OPTION 2: Add UniqueTogetherValidator (optional, adds extra DB query)
class JournalContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalContact
        fields = ['id', 'journal', 'contact', 'created_at']
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=JournalContact.objects.all(),
                fields=['journal', 'contact'],
                message='Contact already in journal'
            )
        ]
```

**Tradeoff:** UniqueTogetherValidator adds an extra SELECT query before INSERT. For high-throughput APIs, catching IntegrityError is more efficient.

### Pattern 6: Nested Filtering (Journal → Contacts)
**What:** Provide search/filter on journal detail endpoint, not separate endpoint
**When to use:** When client needs "contacts in THIS journal" view
**Example:**
```python
# Add to JournalDetailSerializer
class JournalDetailSerializer(serializers.ModelSerializer):
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = Journal
        fields = ['id', 'name', 'goal_amount', 'deadline', 'contacts']

    def get_contacts(self, obj):
        # Apply search from query params
        request = self.context.get('request')
        search = request.query_params.get('search', '') if request else ''

        queryset = obj.journal_contacts.select_related('contact')

        if search:
            queryset = queryset.filter(
                Q(contact__first_name__icontains=search) |
                Q(contact__last_name__icontains=search) |
                Q(contact__email__icontains=search)
            )

        return ContactSerializer(
            [jc.contact for jc in queryset],
            many=True
        ).data
```

**Alternative:** Use query params on list endpoint:
```
GET /api/v1/journal-members/?journal_id=<uuid>&search=john
```

### Anti-Patterns to Avoid

- **Don't add contacts to Journal.contacts ManyToManyField directly** - Use JournalContact through-table for explicit control and future extensibility
- **Don't forget transaction.atomic()** - Phase 2 roadmap explicitly calls out atomic transaction bugs as a pitfall
- **Don't use nested serializers for write operations** - DRF's nested writes are complex and error-prone; use flat structure with through-table
- **Don't filter without select_related** - Always optimize querysets before filtering to prevent N+1 queries
- **Don't expose DELETE on collection endpoint** - Only allow DELETE on individual JournalContact resources to prevent accidental bulk deletes

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Search functionality | Custom Q() filter logic in views | DRF SearchFilter with search_fields | Handles multiple terms, case-insensitivity, sanitization |
| Filtering by status/stage | Manual query param parsing | DjangoFilterBackend with filterset_fields | Already configured, handles type coercion, validation |
| Duplicate membership detection | Manual .exists() checks before create | Database unique_together + IntegrityError handling | Database is source of truth, prevents race conditions |
| Query optimization | Manual query construction | select_related() and prefetch_related() | Django ORM optimizes JOINs, handles edge cases |
| Bulk operations | Custom bulk create/delete endpoints | Keep it simple - single add/remove only | Bulk operations risky for journals (accidental deletes), add if needed later |
| Pagination | Custom page slicing | StandardPagination (already configured) | Handles edge cases, consistent across API |

**Key insight:** DRF and Django ORM already solve 90% of API development problems. Phase 2 should leverage these tools rather than building custom solutions.

## Common Pitfalls

### Pitfall 1: Atomic Transaction Scope Bugs (FROM ROADMAP)
**What goes wrong:** Race conditions cause duplicate memberships, orphaned events, or integrity errors
**Why it happens:** Multiple concurrent requests modify relationships without transaction isolation
**How to avoid:**
```python
# Wrap ALL membership mutations in atomic blocks
from django.db import transaction, IntegrityError

@transaction.atomic
def perform_create(self, serializer):
    journal_contact = serializer.save()
    # Any related operations (events, notifications) happen in same transaction

# Or use context manager in create()
def create(self, request, *args, **kwargs):
    try:
        with transaction.atomic():
            # Validation + creation + event logging
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            # Log event in same transaction
            from apps.events.models import Event
            Event.objects.create(...)

            return Response(serializer.data, status=201)
    except IntegrityError as e:
        return Response({'detail': 'Already exists'}, status=400)
```
**Warning signs:**
- IntegrityError exceptions in production logs
- "Contact already in journal" errors despite UI preventing duplicates
- Events created but membership missing (or vice versa)

### Pitfall 2: N+1 Queries from Related Fields
**What goes wrong:** API becomes slow as journals gain more contacts
**Why it happens:** Forgot select_related() when accessing journal/contact in serializers
**How to avoid:**
```python
# ALWAYS optimize in get_queryset
def get_queryset(self):
    return JournalContact.objects.select_related(
        'journal',
        'contact'
    ).filter(...)

# Verify with django-debug-toolbar or:
from django.db import connection
print(len(connection.queries))  # Should be ~1-3, not 100+
```
**Warning signs:**
- API response time increases linearly with number of contacts
- Database query logs show repeated SELECT statements for same tables

### Pitfall 3: SearchFilter Performance on Large Datasets
**What goes wrong:** Search becomes slow (>1s) when journals have 1000+ contacts
**Why it happens:** DRF's SearchFilter uses `icontains` which can't use PostgreSQL GIN indexes (generates `UPPER(field) LIKE UPPER(value)` instead of `field ILIKE value`)
**How to avoid:**
```python
# For small datasets (<10k contacts): Use built-in SearchFilter (fine)
search_fields = ['contact__first_name', 'contact__last_name']

# For large datasets: Add database index and use custom filter
# In migration:
from django.contrib.postgres.operations import TrigramExtension

class Migration(migrations.Migration):
    operations = [
        TrigramExtension(),  # Enable pg_trgm
        migrations.AddIndex(
            model_name='contact',
            index=GinIndex(
                fields=['first_name', 'last_name'],
                name='contact_name_gin_idx',
                opclasses=['gin_trgm_ops', 'gin_trgm_ops']
            )
        )
    ]

# Then use custom FilterBackend that generates ILIKE queries
```
**Warning signs:**
- Search queries take >500ms on production
- EXPLAIN ANALYZE shows sequential scans instead of index usage

### Pitfall 4: Exposing Internal IDs in URLs
**What goes wrong:** URLs expose JournalContact.id which is meaningless to users
**Why it happens:** Generic views default to using model PK
**How to avoid:**
```python
# Use composite lookup (journal_id + contact_id) for meaningful URLs
# DELETE /api/v1/journals/{journal_id}/contacts/{contact_id}/

class JournalContactDestroyView(generics.DestroyAPIView):
    def get_object(self):
        journal_id = self.kwargs['journal_id']
        contact_id = self.kwargs['contact_id']

        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.get(
            journal_id=journal_id,
            contact_id=contact_id
        )
        self.check_object_permissions(self.request, obj)
        return obj
```
**Warning signs:**
- Frontend has to store JournalContact IDs separately from journal/contact IDs
- DELETE requests require extra lookup to find JournalContact.id

### Pitfall 5: Missing Permission Checks on Through-Table
**What goes wrong:** User can add ANY contact to their journal, including contacts owned by others
**Why it happens:** Permission only checks journal ownership, not contact ownership
**How to avoid:**
```python
# Validate in serializer that contact belongs to same owner
class JournalContactSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        journal = attrs['journal']
        contact = attrs['contact']
        user = self.context['request'].user

        # Ensure user owns the journal
        if journal.owner != user and user.role != 'admin':
            raise serializers.ValidationError(
                "You don't have permission to modify this journal"
            )

        # Ensure user owns the contact
        if contact.owner != user and user.role != 'admin':
            raise serializers.ValidationError(
                "You can only add your own contacts"
            )

        return attrs
```
**Warning signs:**
- Staff users can add admin's contacts to their journals
- Cross-owner contact sharing (if not intended feature)

### Pitfall 6: Catching Too Many Exceptions
**What goes wrong:** Real errors (permission denied, validation failures) hidden behind generic IntegrityError handler
**Why it happens:** Overly broad try/except catches all database errors
**How to avoid:**
```python
# Be specific about what you catch
from django.db import IntegrityError
from django.db.utils import DatabaseError

def create(self, request, *args, **kwargs):
    try:
        with transaction.atomic():
            return super().create(request, *args, **kwargs)
    except IntegrityError as e:
        # Only catch unique_together violations
        if 'unique constraint' in str(e).lower():
            return Response(
                {'detail': 'Contact already in journal'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Re-raise other integrity errors
        raise
    # Don't catch DatabaseError, ValidationError, etc.
```
**Warning signs:**
- All database errors return "Already exists" message
- Hard to debug actual issues (permission errors look like duplicates)

### Pitfall 7: Forgetting to Filter Archived Journals
**What goes wrong:** Search returns contacts from archived journals
**Why it happens:** Phase 1 implemented is_archived but forgot to exclude in Phase 2 queries
**How to avoid:**
```python
def get_queryset(self):
    queryset = JournalContact.objects.select_related('journal', 'contact')

    # Exclude archived journals
    queryset = queryset.filter(journal__is_archived=False)

    # Unless explicitly requested
    if self.request.query_params.get('include_archived') == 'true':
        queryset = JournalContact.objects.select_related('journal', 'contact')

    return queryset
```
**Warning signs:**
- Users see contacts from old/archived journals in search results
- Contact appears in multiple journals (one archived, one active)

## Code Examples

Verified patterns from official sources:

### Complete JournalContact Create View
```python
# Source: DRF patterns + Django atomic transactions best practices
from django.db import transaction, IntegrityError
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class JournalContactListCreateView(generics.ListCreateAPIView):
    """
    GET: List contacts in journal(s) with search/filter
    POST: Add contact to journal
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JournalContactSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        'contact__first_name',
        'contact__last_name',
        'contact__email'
    ]
    filterset_fields = ['contact__status']

    def get_queryset(self):
        user = self.request.user

        # Base queryset with optimization
        queryset = JournalContact.objects.select_related(
            'journal',
            'contact'
        )

        # Scope by ownership
        if user.role != 'admin':
            queryset = queryset.filter(journal__owner=user)

        # Exclude archived journals
        queryset = queryset.filter(journal__is_archived=False)

        # Filter by specific journal if provided
        journal_id = self.request.query_params.get('journal_id')
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create membership with atomic transaction."""
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED,
                    headers=headers
                )
        except IntegrityError as e:
            if 'unique constraint' in str(e).lower():
                return Response(
                    {'detail': 'Contact already in this journal'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            raise
```

### JournalContact Serializer with Validation
```python
# Source: DRF serializer validation patterns
from rest_framework import serializers
from apps.journals.models import JournalContact

class JournalContactSerializer(serializers.ModelSerializer):
    # Nested contact details for read
    contact_name = serializers.CharField(
        source='contact.full_name',
        read_only=True
    )
    contact_email = serializers.EmailField(
        source='contact.email',
        read_only=True
    )

    class Meta:
        model = JournalContact
        fields = [
            'id',
            'journal',
            'contact',
            'contact_name',
            'contact_email',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """Ensure user owns both journal and contact."""
        journal = attrs['journal']
        contact = attrs['contact']
        user = self.context['request'].user

        # Admin can add any contact to any journal
        if user.role == 'admin':
            return attrs

        # Validate journal ownership
        if journal.owner != user:
            raise serializers.ValidationError({
                'journal': 'You can only add contacts to your own journals'
            })

        # Validate contact ownership
        if contact.owner != user:
            raise serializers.ValidationError({
                'contact': 'You can only add your own contacts'
            })

        return attrs
```

### Delete JournalContact View
```python
# Source: DRF DestroyAPIView pattern
class JournalContactDestroyView(generics.DestroyAPIView):
    """
    DELETE: Remove contact from journal
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = JournalContactSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = JournalContact.objects.select_related('journal', 'contact')

        if user.role != 'admin':
            queryset = queryset.filter(journal__owner=user)

        return queryset

    @transaction.atomic
    def perform_destroy(self, instance):
        """Delete with atomic transaction."""
        instance.delete()
```

### URL Patterns
```python
# Source: Django URL patterns for nested resources
from django.urls import path
from apps.journals.views import (
    JournalContactListCreateView,
    JournalContactDestroyView,
)

app_name = 'journals'

urlpatterns = [
    # ... existing journal endpoints

    # Journal membership endpoints
    path(
        'journal-members/',
        JournalContactListCreateView.as_view(),
        name='journal-member-list'
    ),
    path(
        'journal-members/<uuid:pk>/',
        JournalContactDestroyView.as_view(),
        name='journal-member-delete'
    ),
]
```

### Search Usage Examples
```bash
# Search contacts within a journal
GET /api/v1/journals/journal-members/?journal_id=<uuid>&search=john

# Filter by contact status
GET /api/v1/journals/journal-members/?journal_id=<uuid>&contact__status=donor

# Combine search and filter
GET /api/v1/journals/journal-members/?journal_id=<uuid>&search=smith&contact__status=prospect

# Add contact to journal
POST /api/v1/journals/journal-members/
{
  "journal": "<journal-uuid>",
  "contact": "<contact-uuid>"
}

# Remove contact from journal
DELETE /api/v1/journals/journal-members/<journal-contact-uuid>/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual M2M with .add() | Through-table as REST resource | DRF best practice | Explicit control, extensibility, clear API |
| UniqueTogetherValidator | Database constraint + IntegrityError handling | Django 2.2+ | Better performance, prevents race conditions |
| Nested serializer writes | Flat structure with through-table | DRF 3.x | Simpler, more reliable, easier testing |
| Custom search logic | DRF SearchFilter | DRF standard | Consistent API, handles edge cases |
| Manual transaction management | transaction.atomic() decorator/context manager | Django best practice | Prevents data inconsistency |

**Deprecated/outdated:**
- `unique_together` in Meta (still works but Django 2.2+ prefers `UniqueConstraint` in Meta.constraints)
- Manual SQL for bulk operations (use Django ORM bulk_create, bulk_update)

## Open Questions

Things that couldn't be fully resolved:

1. **Nested Routes vs Flat Routes**
   - What we know: Nested routes (/journals/{id}/members/) are more RESTful but require extra URL configuration
   - What's unclear: Does existing codebase prefer nested or flat URL patterns?
   - Recommendation: Use flat routes (/journal-members/?journal_id=X) to match existing patterns in pledges, donations apps

2. **Search on Journal Detail vs Separate Endpoint**
   - What we know: Can implement search as query params on journal detail OR as separate filtered list endpoint
   - What's unclear: Which approach does frontend prefer?
   - Recommendation: Implement both - journal detail can include contact_count, separate endpoint provides searchable list

3. **Contact Picker Implementation**
   - What we know: Requirement says "contacts can be added via 'Add Contacts' picker dialog"
   - What's unclear: Is this frontend-only (API just provides available contacts) or backend search endpoint?
   - Recommendation: Provide GET /api/v1/contacts/?exclude_journal_id=X endpoint to get contacts not yet in journal

4. **Event Logging for Membership Changes**
   - What we know: Phase 1 uses signals for event creation
   - What's unclear: Should adding/removing contacts create events? What EventType to use?
   - Recommendation: Add JOURNAL_CONTACT_ADDED and JOURNAL_CONTACT_REMOVED event types if audit trail needed

5. **Stage Filtering Implementation**
   - What we know: Success criteria mentions "filter by stage" but JournalContact has no stage field
   - What's unclear: Is stage stored on JournalContact or derived from latest JournalStageEvent?
   - Recommendation: Add current_stage field to JournalContact (denormalized) OR implement as complex filter on latest event

6. **Decision Status Filtering**
   - What we know: Success criteria mentions "filter by decision status"
   - What's unclear: What is decision status? Is it part of pipeline stage or separate field?
   - Recommendation: Clarify with product owner - likely ties to JournalStageEvent decisions

## Sources

### Primary (HIGH confidence)
- https://www.django-rest-framework.org/api-guide/filtering/ - Official DRF filtering documentation
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/ - Official Django atomic transactions documentation
- https://www.django-rest-framework.org/api-guide/relations/ - Official DRF serializer relations documentation
- https://www.django-rest-framework.org/api-guide/validators/ - Official DRF validators documentation
- /home/matkukla/projects/DonorCRM/apps/journals/models.py - Existing JournalContact model
- /home/matkukla/projects/DonorCRM/apps/journals/views.py - Existing view patterns
- /home/matkukla/projects/DonorCRM/apps/core/permissions.py - Permission patterns

### Secondary (MEDIUM confidence)
- [Building a Many-to-Many Modeled REST API with Django Rest Framework](https://kingsleytorlowei.medium.com/building-a-many-to-many-modelled-rest-api-with-django-rest-framework-d41f54fe372) - Practical through-table patterns
- [Optimizing Django Queries with select_related and prefetch_related](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb) - Query optimization guide
- [Understanding Django's Transaction Atomic](https://plainenglish.io/blog/understanding-djangos-transaction-atomic) - Transaction best practices

### Tertiary (LOW confidence)
- WebSearch results on DRF bulk operations - flagged as potentially risky, recommend avoiding for Phase 2
- WebSearch on SearchFilter performance - identified issue but solution requires testing on actual dataset

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and verified
- Architecture patterns: HIGH - DRF and Django official documentation + existing codebase patterns
- Atomic transactions: HIGH - Official Django docs explicitly cover this pattern
- Search/filter implementation: HIGH - DRF built-in features well-documented
- Query optimization: HIGH - Django ORM select_related/prefetch_related are standard
- URL structure: MEDIUM - Existing patterns suggest flat routes but nested is also valid
- Stage/decision filtering: LOW - Unclear from requirements how these fields are modeled

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - Django 4.2 LTS stable, DRF 3.14 mature)
