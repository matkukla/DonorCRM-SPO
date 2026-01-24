# Technology Stack: Journal/Pipeline Feature

**Project:** DonorCRM - Fundraising Pipeline Management System
**Researched:** 2026-01-24
**Target Versions:** Django 4.2+, DRF 3.14+, Python 3.11+
**Confidence Level:** HIGH (Context7 + Official Docs + Project Review)

## Executive Summary

The Journal/Pipeline feature requires tracking contacts through 6 pipeline stages with append-only event logging, complex nested relationships, and owner-scoped permissions. This research recommends a stack combining Django's TimeStampedModel pattern, UUID primary keys, and DRF's nested serializer patterns with explicit QuerySet optimization.

---

## Recommended Stack

### Core Models & Database Patterns

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Django TimeStampedModel | 4.2+ | Base model for all pipeline entities | Already implemented in DonorCRM; provides UUID PK + auto timestamps |
| Django JSONField | 4.2+ | Store structured pipeline state & metadata | Native support, JSONB on PostgreSQL, validates inline data |
| DecimalField | 4.2+ | Money storage (amounts in cents as integers) | Avoids floating-point errors; use max_digits=12, decimal_places=2 |
| Django Signals | 4.2+ | Append-only event logging | Built-in, efficient for post_save hooks to create events |
| Pydantic (optional) | 2.0+ | Validate JSON field structure | Best practice for enforcing pipeline state schema |

### DRF Serializers

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| DRF ModelSerializer | 3.14+ | Base serializer class | Type-safe, validates against model fields |
| DRF Nested Serializers | 3.14+ | journal → contacts → events | Read-only nested by default; explicit create/update methods required |
| DRF PrimaryKeyRelatedField | 3.14+ | Foreign key relationships | Lightweight, ID-only; use for list views |
| DRF StringRelatedField | 3.14+ | Display related object string repr | Use for read-only status/choice fields |

### DRF ViewSets & Routing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| DRF ModelViewSet | 3.14+ | List/Create/Retrieve/Update/Delete | All journal operations via standard REST actions |
| DRF DefaultRouter | 3.14+ | URL generation | Auto-generates /journals/, /journals/{id}/ patterns |
| drf-nested-routers | 0.1.x | Nested resource routing | journal/{id}/contacts/{id}/events/ patterns |
| @action decorator | 3.14+ | Custom actions | Transition pipeline stage: POST /journals/{id}/advance_stage/ |

### Query Optimization

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| select_related() | 4.2+ | ForeignKey/OneToOne prefetch | Journal → Owner, Contact → Owner (SQL JOIN) |
| prefetch_related() | 4.2+ | ManyToMany/reverse FK prefetch | Journal → Contacts → Events (separate queries + Python merge) |
| Prefetch object | 4.2+ | Custom prefetch with filters | Prefetch only recent events: `Prefetch('events', queryset=Event.objects.filter(created_at__gte=...))` |
| defer()/only() | 4.2+ | Field-level optimization | Defer large TextField fields until detail view |

### Permissions & Security

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| DRF BasePermission | 3.14+ | Custom permission classes | Implement owner-scoped + admin-visible access |
| IsAuthenticated | 3.14+ | Require login | All journal endpoints authenticated |
| Custom IsOwnerOrAdminReadOnly | 3.14+ | Owner scoped with admin visibility | Contacts visible by owner or admin; finance read-only |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | 3.x | Filtering querysets | Pipeline stage filtering, date range filtering |
| drf-spectacular | 0.27+ | OpenAPI schema generation | Auto-doc for Journal/Event endpoints |
| django-model-utils | 4.5+ | ChoicesEnum, StatusModel mixin | Pipeline stage choices with transitions |
| celery (optional) | 5.3+ | Async background jobs | Bulk stage transitions, email notifications |

---

## Recommended Architecture Decisions

### 1. Django Model Patterns for Pipeline Tracking

#### Journal Model Structure
```python
from django.db import models
from apps.core.models import TimeStampedModel

class PipelineStage(models.TextChoices):
    """6-stage fundraising pipeline."""
    CONTACT = 'contact', 'Contact'
    MEET = 'meet', 'Meet'
    CLOSE = 'close', 'Close'
    DECISION = 'decision', 'Decision'
    THANK = 'thank', 'Thank'
    NEXT_STEPS = 'next_steps', 'Next Steps'

class Journal(TimeStampedModel):
    """Campaign pipeline tracking journal."""
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='journals',
        db_index=True
    )

    # Campaign info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Pipeline state (current stage for quick filtering)
    current_stage = models.CharField(
        max_length=20,
        choices=PipelineStage.choices,
        default=PipelineStage.CONTACT,
        db_index=True
    )

    # Milestones (denormalized for grid views)
    stage_entered_at = models.DateTimeField(null=True, blank=True)
    target_close_date = models.DateField(null=True, blank=True)
    expected_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True
    )

    # Append-only tracking via related_name='journal_contacts'

    class Meta:
        db_table = 'journal'
        indexes = [
            models.Index(fields=['owner', 'current_stage']),
            models.Index(fields=['current_stage', 'stage_entered_at']),
            models.Index(fields=['target_close_date']),
        ]
```

#### JournalContact (Join Model)
```python
class JournalContact(TimeStampedModel):
    """Contact membership in a journal (campaign)."""
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        related_name='contacts'
    )

    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='journals'
    )

    # Contact's current stage within this journal
    stage = models.CharField(
        max_length=20,
        choices=PipelineStage.choices,
        db_index=True
    )

    # Notes specific to this contact's progress in journal
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('journal', 'contact')
        indexes = [
            models.Index(fields=['journal', 'stage']),
            models.Index(fields=['contact', 'stage']),
        ]
```

#### JournalEvent (Append-Only Log)
```python
class JournalEventType(models.TextChoices):
    """Types of events in journal pipeline."""
    CREATED = 'created', 'Created'
    STAGE_CHANGED = 'stage_changed', 'Stage Changed'
    NOTE_ADDED = 'note_added', 'Note Added'
    CONTACT_ADDED = 'contact_added', 'Contact Added'
    AMOUNT_UPDATED = 'amount_updated', 'Amount Updated'

class JournalEvent(TimeStampedModel):
    """Append-only event log for journal changes."""
    journal_contact = models.ForeignKey(
        JournalContact,
        on_delete=models.CASCADE,
        related_name='events'
    )

    event_type = models.CharField(
        max_length=30,
        choices=JournalEventType.choices,
        db_index=True
    )

    # Who made the change
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='journal_events'
    )

    # Data snapshot for changes
    metadata = models.JSONField(default=dict, blank=True)
    # Example: {'from_stage': 'contact', 'to_stage': 'meet', 'reason': 'Phone call scheduled'}

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'journal_event'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journal_contact', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]
```

**Key Pattern Decisions:**
- **Append-only events:** Never update JournalEvent, only create new ones
- **Denormalized current_stage:** Fast filtering without JOIN to JournalContact
- **UUID primary keys:** Already in TimeStampedModel base class
- **JSON metadata:** Flexible schema for future event types without migrations

---

### 2. DRF Serializer Patterns for Nested Relationships

#### Read-Only List Serializer (Grid View)
```python
from rest_framework import serializers
from apps.journals.models import Journal, JournalContact, JournalEvent

class JournalContactListSerializer(serializers.ModelSerializer):
    """Minimal contact info for journal grid."""
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    contact_email = serializers.CharField(source='contact.email', read_only=True)

    class Meta:
        model = JournalContact
        fields = ['id', 'contact_id', 'contact_name', 'contact_email', 'stage']
        read_only_fields = fields

class JournalListSerializer(serializers.ModelSerializer):
    """Journal list view with minimal nested data."""
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    contact_count = serializers.SerializerMethodField()

    class Meta:
        model = Journal
        fields = [
            'id', 'title', 'current_stage', 'stage_entered_at',
            'target_close_date', 'expected_amount', 'contact_count',
            'owner', 'owner_name', 'created_at'
        ]
        read_only_fields = [
            'id', 'contact_count', 'owner', 'owner_name', 'created_at'
        ]

    def get_contact_count(self, obj):
        """Count contacts in journal (can be prefetch_related optimized)."""
        return obj.contacts.count()
```

#### Nested Detail Serializer (Avoid Deep Nesting)
```python
class JournalEventSerializer(serializers.ModelSerializer):
    """Events for a journal contact (read-only)."""
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = JournalEvent
        fields = [
            'id', 'event_type', 'created_by_name', 'notes',
            'metadata', 'created_at'
        ]
        read_only_fields = fields

class JournalContactDetailSerializer(serializers.ModelSerializer):
    """Contact within a journal with recent events."""
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    # Only include recent events (last 5) to avoid huge payloads
    events = serializers.SerializerMethodField()

    class Meta:
        model = JournalContact
        fields = [
            'id', 'contact_id', 'contact_name', 'stage',
            'notes', 'events', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'contact_id', 'created_at', 'updated_at']

    def get_events(self, obj):
        """Return last 5 events only."""
        recent_events = obj.events.all()[:5]
        return JournalEventSerializer(recent_events, many=True).data

class JournalDetailSerializer(serializers.ModelSerializer):
    """Journal detail with contacts (but NOT deeply nested events)."""
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    contacts = JournalContactDetailSerializer(
        many=True,
        read_only=True,
        source='contacts'
    )

    class Meta:
        model = Journal
        fields = [
            'id', 'title', 'description', 'current_stage',
            'stage_entered_at', 'target_close_date', 'expected_amount',
            'owner', 'owner_name', 'contacts',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'owner_name', 'contacts',
            'created_at', 'updated_at'
        ]
```

**Key Serializer Patterns:**
- **No depth option:** Use explicit nested serializers instead
- **Limit nested data:** Events return only recent 5, not all
- **Read-only by default:** Nested serializers cannot write
- **source parameter:** Use for custom field mapping without extra queries

---

### 3. Django Signals for Append-Only Event Logging

#### Signal Handlers for Automatic Event Creation
```python
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.journals.models import JournalContact, JournalEvent, JournalEventType

@receiver(pre_save, sender=JournalContact)
def track_journal_contact_changes(sender, instance, **kwargs):
    """
    Track state before save for change detection.
    Must be called BEFORE save to detect changes.
    """
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = JournalContact.objects.get(pk=instance.pk)
            instance._old_stage = old_instance.stage
            instance._old_notes = old_instance.notes
        except JournalContact.DoesNotExist:
            pass

@receiver(post_save, sender=JournalContact)
def create_journal_event_on_contact_change(sender, instance, created, **kwargs):
    """
    Create append-only event after JournalContact save.
    CRITICAL: Never update existing events, only create new ones.
    """
    from django.db import transaction

    # Wrap in transaction.on_commit to ensure atomicity
    def create_event():
        if created:
            # Initial contact added to journal
            JournalEvent.objects.create(
                journal_contact=instance,
                event_type=JournalEventType.CONTACT_ADDED,
                created_by_id=getattr(instance, '_created_by_id', None),
                metadata={'stage': instance.stage},
                notes=f'Contact {instance.contact.full_name} added'
            )
        else:
            # Track stage changes
            old_stage = getattr(instance, '_old_stage', None)
            if old_stage and old_stage != instance.stage:
                JournalEvent.objects.create(
                    journal_contact=instance,
                    event_type=JournalEventType.STAGE_CHANGED,
                    created_by_id=getattr(instance, '_updated_by_id', None),
                    metadata={
                        'from_stage': old_stage,
                        'to_stage': instance.stage,
                        'timestamp': timezone.now().isoformat()
                    },
                    notes=instance.notes if hasattr(instance, '_new_notes') else ''
                )

    transaction.on_commit(create_event)

# Register signals
post_save.connect(create_journal_event_on_contact_change, sender=JournalContact)
pre_save.connect(track_journal_contact_changes, sender=JournalContact)
```

**Key Signal Patterns:**
- **pre_save hook:** Snapshot original values for change detection
- **post_save with transaction.on_commit():** Create events after database commit
- **Never mutate events:** Only create new JournalEvent records
- **Metadata as JSON:** Flexible schema for future event types

---

### 4. DRF ViewSet Patterns for Complex Nested Resources

#### Nested ViewSet with Custom Actions
```python
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.journals.models import Journal, JournalContact, JournalEvent
from apps.journals.serializers import (
    JournalListSerializer,
    JournalDetailSerializer,
    JournalContactListSerializer,
    JournalContactDetailSerializer,
    JournalEventSerializer,
)
from apps.core.permissions import IsOwnerOrAdmin, IsStaffOrAbove

class JournalViewSet(viewsets.ModelViewSet):
    """
    Journal (campaign) management with contacts and events.

    GET    /journals/          - List journals
    POST   /journals/          - Create journal
    GET    /journals/{id}/     - Get journal details
    PATCH  /journals/{id}/     - Update journal
    DELETE /journals/{id}/     - Delete journal
    POST   /journals/{id}/advance_stage/  - Advance journal stage
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAbove]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['current_stage', 'owner']
    ordering_fields = ['created_at', 'stage_entered_at', 'target_close_date']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Optimize queries for list vs detail views.
        Use select_related for owner, prefetch for contacts with their events.
        """
        user = self.request.user

        # Base queryset filtered by ownership
        if user.role == 'admin':
            queryset = Journal.objects.all()
        else:
            queryset = Journal.objects.filter(owner=user)

        # Optimize based on action
        if self.action == 'list':
            # List view: journals with contact counts only
            return queryset.select_related('owner').prefetch_related('contacts')

        elif self.action == 'retrieve':
            # Detail view: full contacts with events
            from django.db.models import Prefetch

            # Prefetch contacts with only recent events
            recent_events = JournalEvent.objects.all()[:5]
            contact_prefetch = Prefetch(
                'contacts__events',
                queryset=recent_events
            )

            return queryset.select_related('owner').prefetch_related(
                'contacts__contact',
                'contacts__created_by',
                contact_prefetch
            )

        return queryset.select_related('owner')

    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == 'list':
            return JournalListSerializer
        return JournalDetailSerializer

    def perform_create(self, serializer):
        """Set owner to current user on creation."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def advance_stage(self, request, pk=None):
        """
        Advance journal to next stage.
        POST /journals/{id}/advance_stage/
        """
        journal = self.get_object()

        # Validate stage transition
        from apps.journals.models import PipelineStage
        stages = [s[0] for s in PipelineStage.choices]
        current_idx = stages.index(journal.current_stage)

        if current_idx >= len(stages) - 1:
            return Response(
                {'detail': 'Journal already at final stage'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Advance stage
        next_stage = stages[current_idx + 1]
        journal.current_stage = next_stage
        journal.stage_entered_at = timezone.now()
        journal.save()

        return Response(
            self.get_serializer(journal).data,
            status=status.HTTP_200_OK
        )


class JournalContactViewSet(viewsets.ModelViewSet):
    """
    Nested resource: contacts within a journal.
    GET    /journals/{journal_id}/contacts/
    POST   /journals/{journal_id}/contacts/
    GET    /journals/{journal_id}/contacts/{id}/
    PATCH  /journals/{journal_id}/contacts/{id}/
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = JournalContactDetailSerializer

    def get_queryset(self):
        """Filter to contacts of a specific journal."""
        journal_id = self.kwargs.get('journal_id')
        user = self.request.user

        # Get journal first (respects ownership)
        journal = get_object_or_404(
            Journal.objects.select_related('owner'),
            id=journal_id,
            owner=user if user.role != 'admin' else None
        )

        return JournalContact.objects.filter(
            journal=journal
        ).select_related('contact', 'created_by').prefetch_related('events')

    def perform_create(self, serializer):
        """Add contact to journal."""
        journal_id = self.kwargs.get('journal_id')
        journal = get_object_or_404(Journal, id=journal_id)

        serializer.save(
            journal=journal,
            _created_by_id=self.request.user.id
        )

    @action(detail=True, methods=['post'])
    def change_stage(self, request, journal_id=None, pk=None):
        """
        Change contact's stage within journal.
        POST /journals/{journal_id}/contacts/{id}/change_stage/
        {"stage": "meet", "notes": "Scheduled for next week"}
        """
        journal_contact = self.get_object()
        new_stage = request.data.get('stage')
        notes = request.data.get('notes', '')

        # Validate stage
        from apps.journals.models import PipelineStage
        valid_stages = [s[0] for s in PipelineStage.choices]
        if new_stage not in valid_stages:
            return Response(
                {'detail': f'Invalid stage. Choose from: {valid_stages}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update and trigger event via signal
        journal_contact.stage = new_stage
        journal_contact.notes = notes
        journal_contact._updated_by_id = request.user.id
        journal_contact._new_notes = notes
        journal_contact.save()

        return Response(
            self.get_serializer(journal_contact).data,
            status=status.HTTP_200_OK
        )


class JournalEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only event log for a journal contact.
    GET /journals/{journal_id}/contacts/{contact_id}/events/
    """
    serializer_class = JournalEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    ordering = ['-created_at']

    def get_queryset(self):
        """Events for a specific journal contact."""
        journal_id = self.kwargs.get('journal_id')
        contact_id = self.kwargs.get('contact_id')

        return JournalEvent.objects.filter(
            journal_contact__journal_id=journal_id,
            journal_contact_id=contact_id
        ).select_related('created_by')
```

**Key ViewSet Patterns:**
- **Optimize queryset by action:** List uses basic prefetch, Detail uses Prefetch with filters
- **Custom actions via @action:** Define HTTP method and detail=True/False
- **Nested routing:** kwargs like `journal_id` and `contact_id` from router
- **Permission object-level:** Check journal ownership before accessing contacts
- **Signal integration:** Views set `_created_by_id` attribute for signal handlers

---

### 5. Query Optimization Strategies

#### SELECT_RELATED vs PREFETCH_RELATED Decision Matrix

| Relationship Type | Use | Query Pattern |
|------------------|-----|---------------|
| ForeignKey (Journal → Owner) | select_related | SQL JOIN, single query |
| OneToOneField | select_related | SQL JOIN, single query |
| ManyToManyField (Contact groups) | prefetch_related | N+1 avoided, Python merge |
| Reverse ForeignKey (Journal → Contacts) | prefetch_related | N+1 avoided, Python merge |
| Reverse ManyToManyField | prefetch_related | N+1 avoided, Python merge |

#### Grid View Optimization (List 100s of journals)
```python
# BAD: N+1 query problem
journals = Journal.objects.all()
for journal in journals:
    print(journal.owner.full_name)  # 100 extra queries!

# GOOD: Single JOIN
journals = Journal.objects.select_related('owner').all()

# BETTER: Include contact count
from django.db.models import Count
journals = Journal.objects.select_related('owner').annotate(
    contact_count=Count('contacts')
).all()
```

#### Detail View Optimization (Journal with contacts and events)
```python
from django.db.models import Prefetch

# Prefetch with filtered queryset (last 5 events per contact)
recent_events = JournalEvent.objects.order_by('-created_at')[:5]
contact_prefetch = Prefetch(
    'contacts__events',
    queryset=recent_events
)

journal = Journal.objects.select_related(
    'owner',  # ForeignKey
    'contacts__contact',  # Nested ForeignKey
).prefetch_related(
    'contacts',  # Reverse FK
    contact_prefetch,  # Custom prefetch with filter
).get(id=journal_id)

# Query count: ~4 total
# 1. Journal + Owner (select_related)
# 2. JournalContacts
# 3. Contact objects
# 4. Events
```

**Critical Optimization Rules:**
- **Always use select_related for ForeignKey upstream:** journal.owner, contact.owner
- **Use prefetch_related for ManyToMany & reverse FK:** journal.contacts
- **Combine both:** select_related('contacts__contact') for nested ForeignKey
- **Limit nested results:** Use Prefetch() to apply [:5] or filters
- **Test with django-debug-toolbar:** Verify query counts in development

---

### 6. UUID Primary Keys + TimeStampedModel

Already implemented in your project. Maintain these patterns:

```python
# All models inherit from TimeStampedModel
class Journal(TimeStampedModel):
    # UUID PK auto-generated, created_at/updated_at auto-added
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    ...

# Benefits:
# 1. Non-sequential IDs prevent ID enumeration attacks
# 2. UUIDs globally unique, safe for distributed systems
# 3. auto_now_add/auto_now handle timestamps automatically
# 4. created_at indexed for "recent first" sorting
```

---

### 7. Money Storage Pattern (Cents as Decimals)

For the journal's expected_amount field:

```python
class Journal(TimeStampedModel):
    expected_amount = models.DecimalField(
        max_digits=12,  # Up to $999,999,999.99
        decimal_places=2,  # Cents
        null=True,
        blank=True,
        help_text='Expected donation amount in USD'
    )

    # Usage:
    # journal.expected_amount = Decimal('1000.50')  # $1000.50
    # journal.expected_amount_cents = int(journal.expected_amount * 100)  # 100050
```

**Best Practices:**
- Never use FloatField: loses precision in calculations
- Store as Decimal with 2 decimal places (cents)
- For API: return as string "1000.50" to avoid rounding
- For storage: use ROUND_HALF_EVEN (banker's rounding)
- For calculations: work with Decimal, not float

```python
from decimal import Decimal, ROUND_HALF_EVEN

# Proper rounding
amount = Decimal('10.115')
rounded = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
# Result: 10.12 (standard accounting rounding)
```

---

### 8. Django Permission Patterns for Owner-Scoped + Admin Visibility

Extend your existing permission classes:

```python
# apps/core/permissions.py
from rest_framework import permissions

class IsOwnerOrAdminReadOnly(permissions.BasePermission):
    """
    Journal owner has full access.
    Admin has full access.
    Finance has read-only access.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin: full access
        if user.role == 'admin':
            return True

        # Get owner from object or related field
        owner = getattr(obj, 'owner', None)

        # Owner: full access
        if owner and owner == user:
            return True

        # Finance/read-only: read-only access
        if user.role in ['finance', 'read_only']:
            return request.method in permissions.SAFE_METHODS

        return False


class IsJournalOwner(permissions.BasePermission):
    """Strict check: only journal owner can access."""
    def has_object_permission(self, request, view, obj):
        # For nested resources, check parent journal
        if hasattr(obj, 'journal'):
            journal = obj.journal
        else:
            journal = obj

        user = request.user
        return user.role == 'admin' or journal.owner == user


# Usage in ViewSet:
class JournalViewSet(viewsets.ModelViewSet):
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrAdminReadOnly
    ]
```

**Permission Layering Strategy:**
1. **View-level:** IsAuthenticated + IsStaffOrAbove (role-based)
2. **Object-level:** IsOwnerOrAdminReadOnly (data-scoped)
3. **Action-level:** Override for custom actions (e.g., read-only status endpoint)

---

## Alternatives Considered

| Category | Recommended | Alternative | Trade-offs |
|----------|-------------|-------------|-----------|
| **State Storage** | JSONField + Pydantic | Separate stage fields | JSONField more flexible; separate fields faster |
| **Event Logging** | Django Signals | Celery tasks | Signals simpler; Celery better for async |
| **Nested Routing** | drf-nested-routers | Manual routing | drf-nested-routers standardized; manual more control |
| **Serializer Depth** | Explicit nested classes | depth=2 option | Explicit more maintainable; depth simpler initially |
| **Query Optimization** | select_related + Prefetch | Raw SQL / Django ORM | ORM slower but maintainable; SQL faster but risky |
| **Money Storage** | DecimalField | Money library (django-money) | DecimalField simpler; django-money handles currency |

---

## Installation Guide

### Core Dependencies

```bash
# Already in your project (verify versions)
pip install Django==4.2.x
pip install djangorestframework==3.14.x
pip install django-filter==24.x
pip install drf-spectacular==0.27.x

# Recommended additions
pip install drf-nested-routers==0.1.x
pip install pydantic==2.x  # For JSON schema validation
pip install django-model-utils==4.5.x  # For ChoicesEnum

# Optional for background jobs
pip install celery==5.3.x
pip install celery[redis]==5.3.x
```

### Project Configuration

```python
# config/settings/base.py

INSTALLED_APPS = [
    # ... existing apps ...
    'apps.journals',  # New app for pipeline
]

# DRF settings
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Signal handling (if using append-only events)
INSTALLED_APPS += [
    'apps.journals.apps.JournalsConfig',  # Register signals in ready()
]
```

---

## Summary: Technology Decisions for Journal/Pipeline

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| **Pipeline State Model** | JSONField + denormalized current_stage | Fast filtering + flexible schema |
| **Event Logging** | Append-only JournalEvent table + Django Signals | Immutable audit trail, automatic tracking |
| **Serializers** | Explicit nested classes, no depth option | Type-safe, maintainable, testable |
| **Query Optimization** | select_related for ownership, Prefetch for collections | Eliminates N+1, balances performance |
| **Permissions** | Role-based (view-level) + owner-scoped (object-level) | Follows DonorCRM existing pattern |
| **Money Storage** | DecimalField(max_digits=12, decimal_places=2) | Prevents rounding errors |
| **Routing** | drf-nested-routers for /journals/{id}/contacts/{id}/events | Standard, maintainable nested APIs |
| **ViewSet Actions** | @action decorator for stage transitions | Clear, DRF-standard custom operations |

---

## Sources

- [Django REST Framework - Serializer Relations](https://www.django-rest-framework.org/api-guide/relations/)
- [Django REST Framework - Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
- [Django REST Framework - ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/)
- [Django REST Framework - Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [Optimizing Django Queries with select_related and prefetch_related - Medium](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)
- [Django ORM Performance Optimization - Medium](https://medium.com/@biswajitpanda973/optimizing-django-performance-select-related-prefetch-related-and-the-n-1-problem-76c2db84d73f)
- [Django Audit Logging Best Practices - Medium](https://medium.com/@mariliabontempo/django-audit-logging-the-best-libraries-for-tracking-model-changes-with-postgresql-2c7396564e97)
- [Django Auditlog Documentation](https://django-auditlog.readthedocs.io/en/latest/usage.html)
- [Nested ViewSets with Django REST Framework - browniebroke.com](https://browniebroke.com/blog/2023-05-05-nested-viewsets-with-django-rest-framework/)
- [drf-nested-routers - GitHub](https://github.com/alanjds/drf-nested-routers)
- [Django JSONField - Runebook](https://runebook.dev/en/articles/django_rest_framework/api-guide/fields/index/jsonfield)
- [Enforcing JSON Schema in Django JSONField - Ndifreke Ekott](https://ndifreke-ekott.com/posts/enforcing-json-schema-in-django-jsonfields/)
- [Django Money Documentation](https://django-money.readthedocs.io/)
- [Django Tip: Use DecimalField for money - DEV Community](https://dev.to/koladev/django-tip-use-decimalfield-for-money-3f63)
