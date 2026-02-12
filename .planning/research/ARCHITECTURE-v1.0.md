# Architecture Patterns for Event-Sourced Pipeline Tracking

**Project:** DonorCRM — Journal Feature (Pipeline Tracking with Decision History)
**Research Date:** 2026-01-24
**Focus:** Django event sourcing, nested resource design, permission inheritance, current+history tables

---

## Executive Summary

The Journal feature requires handling append-only pipeline events, mutable decision state with immutable history, and owner-scoped access to nested resources. This research identifies proven patterns from Django's ecosystem and DonorCRM's existing codebase, emphasizing practical implementation over custom frameworks.

**Key Recommendation:** Use a hybrid approach combining:
- **Append-only Event Log** for all stage transitions (Journal → Event lineage)
- **Current + History tables** for decisions (one JournalDecisionCurrent, many JournalDecisionHistory rows)
- **Through model** (JournalContact) for many-to-many with optional metadata
- **Single app (journals)** with clear separation of concerns
- **Nested viewsets** for resource hierarchy with inherited permissions

---

## Pattern 1: Event Sourcing — Append-Only vs State Machines

### Overview

Event sourcing captures every state change as an immutable event. For the Journal's 6-stage pipeline, you have two options:

**Option A: Pure Event Sourcing (Append-Only)**
- Every stage transition is logged as an event (JournalStageEvent)
- Current pipeline state is computed from event history
- Pros: Complete audit trail, temporal queries (state at date X), replayable history
- Cons: Requires computation on read, more complex queries

**Option B: Event Log + Computed State (Recommended)**
- JournalContactStageEvent: Append-only log of every transition
- JournalContactStageState: Denormalized current state (updated on each event)
- Pros: Fast reads, easy materialization, clean separation
- Cons: Need to keep state in sync with events

### Recommendation

**Use Option B** because:
1. DonorCRM already denormalizes state (Contact.status, Task.status)
2. Reports query current state, not history (faster)
3. Django ORM is optimized for state reads, not event replay
4. Lower operational complexity

### Implementation Pattern

```python
# apps/journals/models.py

from django.db import models
from apps.core.models import TimeStampedModel
from django.conf import settings

class JournalStageEvent(TimeStampedModel):
    """
    Append-only event log: every stage transition creates an event.
    This is the system of record for pipeline history.
    """
    STAGE_CHOICES = [
        ('contact', 'Contact'),
        ('meet', 'Meet'),
        ('close', 'Close'),
        ('decision', 'Decision'),
        ('thank', 'Thank You'),
        ('next_steps', 'Next Steps'),
    ]

    EVENT_TYPE_CHOICES = [
        ('stage_entered', 'Stage Entered'),
        ('stage_exited', 'Stage Exited'),
        ('stage_skipped', 'Stage Skipped'),
        ('stage_revisited', 'Stage Revisited'),
        ('note_added', 'Note Added'),
        ('warning_generated', 'Warning Generated'),
    ]

    # Immutable event identity
    journal_contact = models.ForeignKey(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='stage_events'
    )

    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        db_index=True
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        db_index=True
    )

    # Who triggered the event
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='journal_events'
    )

    # Event context
    notes = models.TextField(blank=True, help_text='User notes for this event')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'journal_stage_events'
        ordering = ['created_at']  # Always in order
        indexes = [
            models.Index(fields=['journal_contact', 'stage', 'created_at']),
            models.Index(fields=['journal_contact', 'event_type']),
            models.Index(fields=['created_at']),  # For timeline queries
        ]
        # Prevent accidental updates
        permissions = [
            ('view_journal_stage_event', 'Can view stage events'),
        ]

    def __str__(self):
        return f'{self.journal_contact} - {self.stage}: {self.event_type}'


class JournalContactStageState(TimeStampedModel):
    """
    Computed/denormalized current state: one row per contact+stage.
    Updated whenever a JournalStageEvent is created.
    This powers fast UI queries and "what's the contact doing in this stage?"
    """
    journal_contact = models.OneToOneField(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='stage_state',
        null=True,
        blank=True
    )

    current_stage = models.CharField(
        max_length=20,
        choices=JournalStageEvent.STAGE_CHOICES,
        db_index=True
    )

    # Stage progression tracking
    entered_at = models.DateTimeField()
    last_activity_at = models.DateTimeField()
    event_count = models.PositiveIntegerField(default=0)

    # Flexible progression flags
    is_blocked = models.BooleanField(
        default=False,
        help_text='True if warnings should prevent progression'
    )
    skipped = models.BooleanField(
        default=False,
        help_text='True if this stage was skipped'
    )
    revisited = models.BooleanField(
        default=False,
        help_text='True if contact revisited this stage'
    )

    class Meta:
        db_table = 'journal_contact_stage_state'
        indexes = [
            models.Index(fields=['journal_contact', 'current_stage']),
            models.Index(fields=['current_stage', 'last_activity_at']),
        ]

    def __str__(self):
        return f'{self.journal_contact} - {self.current_stage}'
```

### When Event Sourcing Adds Value

Use explicit query for historical events when:
- Showing "timeline" of contact's journey
- Generating reports: "How long did contact spend in Meet stage?"
- Auditing: "What did staff do on 2026-01-15?"

```python
# Query: Timeline of events for a contact in a journal
events = JournalStageEvent.objects.filter(
    journal_contact__journal=journal,
    journal_contact__contact=contact
).order_by('created_at').select_related('triggered_by')

# Query: Report - Average time per stage
from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.db.models.functions import Lag

events_with_lag = JournalStageEvent.objects.filter(
    journal_contact__journal=journal
).annotate(
    previous_created_at=Lag('created_at')
).filter(
    event_type='stage_entered'
)
# Use this for: average stage duration calculations
```

---

## Pattern 2: Current + History Tables for Decisions

### The Problem

Decision state is mutable: a contact can change their pledge amount, cadence, or decision status multiple times. Yet you need:
1. **Fast access** to current decision: "What is Jane committing?"
2. **Complete history**: "How many times did Jane change her mind?"

### The Solution: Dual-Table Pattern

```python
# apps/journals/models.py

class JournalDecisionCurrent(TimeStampedModel):
    """
    Current/mutable decision state: one row per journal+contact.
    Read from for "what is the current state" queries.
    Updated when decision changes.
    """

    DECISION_STATUS = [
        ('undecided', 'Undecided'),
        ('considering', 'Considering'),
        ('committed', 'Committed'),
        ('declined', 'Declined'),
        ('pending_review', 'Pending Review'),
    ]

    CADENCE_CHOICES = [
        ('one_time', 'One-Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('other', 'Other'),
    ]

    journal_contact = models.OneToOneField(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='decision_current'
    )

    # Current commitment
    status = models.CharField(
        max_length=20,
        choices=DECISION_STATUS,
        default='undecided',
        db_index=True
    )

    # Amount committed (in cents for precision)
    amount_cents = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )

    # Giving cadence
    cadence = models.CharField(
        max_length=20,
        choices=CADENCE_CHOICES,
        null=True,
        blank=True
    )

    # Notes on decision
    notes = models.TextField(blank=True)

    # Last changed
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When was this decision made/confirmed?'
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'journal_decision_current'
        verbose_name_plural = 'journal decision currents'
        indexes = [
            models.Index(fields=['journal_contact']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.journal_contact} - {self.status}: ${self.amount_cents or 0 / 100}'


class JournalDecisionHistory(TimeStampedModel):
    """
    Immutable history: appended to whenever decision changes.
    Full audit trail of every decision iteration.
    """

    journal_contact = models.ForeignKey(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='decision_history'
    )

    # Snapshot of state at this history entry
    status = models.CharField(
        max_length=20,
        choices=JournalDecisionCurrent.DECISION_STATUS
    )
    amount_cents = models.BigIntegerField(null=True, blank=True)
    cadence = models.CharField(
        max_length=20,
        choices=JournalDecisionCurrent.CADENCE_CHOICES,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)

    # Who made this decision
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='decision_changes'
    )

    # Why (optional)
    change_reason = models.TextField(blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'journal_decision_history'
        ordering = ['created_at']  # Always chronological
        indexes = [
            models.Index(fields=['journal_contact', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.journal_contact} - {self.status} on {self.created_at.date()}'
```

### Usage Pattern

**Fast current state query:**
```python
# Get current decision for contact in journal
decision = JournalDecisionCurrent.objects.get(
    journal_contact__journal=journal,
    journal_contact__contact=contact
)
# Instant: one indexed lookup
```

**Full history for UI timeline:**
```python
# Show decision evolution
history = JournalDecisionHistory.objects.filter(
    journal_contact__journal=journal,
    journal_contact__contact=contact
).order_by('created_at')
# Returns all changes in chronological order
```

**Update pattern (in a service/mutation function):**
```python
def update_decision(journal_contact, new_status, amount_cents, cadence, changed_by):
    """Atomically update current and append to history."""

    # Record the history before updating
    JournalDecisionHistory.objects.create(
        journal_contact=journal_contact,
        status=journal_contact.decision_current.status,
        amount_cents=journal_contact.decision_current.amount_cents,
        cadence=journal_contact.decision_current.cadence,
        notes=journal_contact.decision_current.notes,
        changed_by=changed_by,
        change_reason='Decision updated via journal'
    )

    # Update current state
    journal_contact.decision_current.status = new_status
    journal_contact.decision_current.amount_cents = amount_cents
    journal_contact.decision_current.cadence = cadence
    journal_contact.decision_current.decided_at = timezone.now()
    journal_contact.decision_current.save()
```

### Why Not Django-Simple-History?

**django-simple-history** automates history tables but adds overhead:
- Creates a historical table for every tracked model
- Watches all field changes (noisy for mostly-read tables)
- Slower for write-heavy models

**Recommended instead:** Explicit dual-table pattern for decisions because:
1. Decision changes are infrequent (user decision, not system-generated)
2. You control exactly what gets logged (intentional events, not all changes)
3. Lighter weight for DonorCRM's scale
4. Explicit business logic is clearer

---

## Pattern 3: Many-to-Many with Through Model (Journal ↔ Contact)

### The Problem

A contact belongs to multiple journals, and a journal contains multiple contacts. But you also need to track:
- When was this contact added to this journal?
- What's their current decision in this journal context?
- What stage are they in for THIS journal (not globally)?

### Solution: Explicit Through Model

```python
# apps/journals/models.py

class JournalContact(TimeStampedModel):
    """
    Explicit through model: journal membership with state.
    One row = one contact's journey through one journal.
    """

    journal = models.ForeignKey(
        'Journal',
        on_delete=models.CASCADE,
        related_name='members'  # journal.members.all()
    )

    contact = models.ForeignKey(
        'contacts.Contact',
        on_delete=models.CASCADE,
        related_name='journals'  # contact.journals.all()
    )

    # Membership metadata
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='journal_contact_additions'
    )

    # Optional: track why this contact was added
    notes = models.TextField(blank=True, help_text='Why was this contact added?')

    # Status in THIS journal (not global contact status)
    is_active = models.BooleanField(
        default=True,
        help_text='Is contact still active in this journal?'
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    # Indexed for fast lookups
    class Meta:
        db_table = 'journal_contacts'
        unique_together = [('journal', 'contact')]  # Can't add same contact twice
        indexes = [
            models.Index(fields=['journal', 'is_active']),
            models.Index(fields=['contact', 'is_active']),
            models.Index(fields=['journal', 'added_at']),
        ]

    def __str__(self):
        return f'{self.contact.full_name} in {self.journal.name}'


class Journal(TimeStampedModel):
    """
    A fundraising campaign/push: tracks a set of contacts through pipeline.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journals'
    )

    # Campaign info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Goal
    goal_amount_cents = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True
    )
    goal_deadline = models.DateField(null=True, blank=True)

    # Status
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    # Relationships (via through model)
    contacts = models.ManyToManyField(
        'contacts.Contact',
        through='JournalContact',
        related_name='journal_set'  # Keep distinct from existing .journals
    )

    class Meta:
        db_table = 'journals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_archived']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name
```

### Usage Patterns

**Add a contact to a journal:**
```python
JournalContact.objects.create(
    journal=journal,
    contact=contact,
    added_by=request.user,
    notes='Prospect for Spring support raising'
)
```

**List contacts in a journal:**
```python
journal.members.filter(is_active=True).select_related('contact').order_by('added_at')
```

**List journals a contact is in:**
```python
contact.journals.filter(journalcontact__is_active=True)
```

### Why Explicit Through Model Over ManyToManyField

| Aspect | Plain M2M | Through Model |
|--------|----------|---------------|
| Extra fields | Not possible | Full Django model |
| Timestamps | Manual tracking | Automatic (TimeStampedModel) |
| Access control | N/A | Can query/filter on membership |
| Audit trail | Requires signals | Natural (changed_by field) |
| Performance | Simple joins | Same as M2M, more control |

**Recommendation:** Use through model because you have extra fields (added_by, notes, is_active).

---

## Pattern 4: Django App Structure — Single App Approach

### The Decision

**Option A: Single journals app** (containing Journal, JournalContact, JournalStageEvent, JournalDecisionCurrent, JournalDecisionHistory)

**Option B: Multiple apps** (journals.core, journals.events, journals.decisions)

### Recommendation: Single App

**Use a single `journals` app** because:

1. **High cohesion**: All models relate to the journal feature
2. **Bounded context**: Journal business logic is self-contained
3. **Easier imports**: `from apps.journals.models import Journal`
4. **Simpler testing**: One test module, not scattered
5. **Follows DonorCRM pattern**: Existing apps (contacts, tasks, donations) are single-app features

**When to reconsider multi-app:**
- If you had independent "events" and "reporting" services
- If events library was reusable across other features
- If team was large enough to split work by subsystem

### App Structure

```
apps/journals/
├── __init__.py
├── admin.py                 # Register models in Django admin
├── apps.py                  # App config
├── migrations/              # Auto-generated
├── models.py                # All 5 models (Journal, JournalContact, Events, Decisions)
├── serializers.py           # All serializers
├── views.py                 # All viewsets
├── permissions.py           # Custom permission classes
├── filters.py               # DjangoFilterBackend filters
├── services.py              # Business logic (decision updates, event creation)
├── urls.py                  # URL routing
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_permissions.py
    └── test_services.py
```

**Key: services.py** for business logic not in models

```python
# apps/journals/services.py

from django.utils import timezone
from apps.journals.models import (
    JournalContact, JournalDecisionCurrent, JournalDecisionHistory,
    JournalStageEvent
)

class JournalService:
    """
    Business logic for journal operations.
    Keeps models clean, logic testable.
    """

    @staticmethod
    def update_decision(journal_contact, new_status, amount_cents, cadence, user, reason=''):
        """Update decision: append to history, update current."""
        # Append to history first (immutable)
        JournalDecisionHistory.objects.create(
            journal_contact=journal_contact,
            status=journal_contact.decision_current.status,
            amount_cents=journal_contact.decision_current.amount_cents,
            cadence=journal_contact.decision_current.cadence,
            changed_by=user,
            change_reason=reason
        )

        # Update current
        journal_contact.decision_current.status = new_status
        journal_contact.decision_current.amount_cents = amount_cents
        journal_contact.decision_current.cadence = cadence
        journal_contact.decision_current.decided_at = timezone.now()
        journal_contact.decision_current.save()

        return journal_contact.decision_current

    @staticmethod
    def log_stage_event(journal_contact, stage, event_type, user, notes='', metadata=None):
        """Log a stage event."""
        event = JournalStageEvent.objects.create(
            journal_contact=journal_contact,
            stage=stage,
            event_type=event_type,
            triggered_by=user,
            notes=notes,
            metadata=metadata or {}
        )

        # Update stage state
        state, _ = JournalContactStageState.objects.get_or_create(
            journal_contact=journal_contact
        )
        state.current_stage = stage
        state.last_activity_at = timezone.now()
        state.event_count = JournalStageEvent.objects.filter(
            journal_contact=journal_contact
        ).count()
        state.save()

        return event

    @staticmethod
    def move_to_stage(journal_contact, new_stage, user, allow_backward=False):
        """
        Move contact to a new stage (flexible pipeline).
        Returns (success, warning_message).
        """
        current_state = journal_contact.stage_state
        current_stage_order = {
            'contact': 1, 'meet': 2, 'close': 3,
            'decision': 4, 'thank': 5, 'next_steps': 6
        }

        old_order = current_stage_order.get(current_state.current_stage, 0)
        new_order = current_stage_order.get(new_stage, 0)

        warning = None

        # Check: backward movement (revisit)
        if new_order < old_order and not allow_backward:
            warning = f'Moving backward from {current_state.current_stage} to {new_stage}'

        # Check: skipping stages
        if new_order > old_order + 1:
            warning = f'Skipping stages: {new_stage} is 2+ stages ahead'

        # Record event
        JournalService.log_stage_event(
            journal_contact,
            new_stage,
            'stage_skipped' if new_order > old_order + 1 else
            'stage_revisited' if new_order < old_order else
            'stage_entered',
            user,
            notes=f'Moved from {current_state.current_stage} to {new_stage}'
        )

        return (True, warning)
```

---

## Pattern 5: API Design — Nested Resources

### The Challenge

How do you expose:
- /journals/ — list all journals
- /journals/{id}/ — get one journal with its members
- /journals/{id}/members/ — list contacts in journal
- /journals/{id}/members/{contact_id}/ — get one contact's state
- /journals/{id}/members/{contact_id}/events/ — get that contact's stage events

### Solution: Nested Viewsets + DRF-Nested-Routers

**Option A: Flat endpoints** (simpler)
```
GET /journals/
GET /journals/{id}/
POST /journal-members/?journal={id}
GET /journal-members/?journal={id}
GET /journal-members/{id}/
GET /journal-stage-events/?journal_contact={id}
```

**Option B: Nested URLs** (RESTful, complex)
```
GET /journals/
GET /journals/{id}/
GET /journals/{id}/members/
GET /journals/{id}/members/{contact_id}/
GET /journals/{id}/members/{contact_id}/events/
```

### Recommendation: Hybrid Approach

Use **flat endpoints** for the API backbone with **optional query params for filtering**:

```python
# apps/journals/urls.py

from rest_framework.routers import DefaultRouter
from .views import JournalViewSet, JournalMemberViewSet, JournalEventViewSet

router = DefaultRouter()
router.register(r'journals', JournalViewSet, basename='journal')
router.register(r'journal-members', JournalMemberViewSet, basename='journal-member')
router.register(r'journal-events', JournalEventViewSet, basename='journal-event')

urlpatterns = router.urls

# Resulting endpoints:
# GET /api/v1/journals/
# POST /api/v1/journals/
# GET /api/v1/journals/{id}/
# PATCH /api/v1/journals/{id}/
#
# GET /api/v1/journal-members/?journal={id}
# POST /api/v1/journal-members/  (requires: journal_id, contact_id)
# GET /api/v1/journal-members/{id}/
# DELETE /api/v1/journal-members/{id}/
#
# GET /api/v1/journal-events/?journal_contact={id}
# GET /api/v1/journal-events/?journal={id}&stage=decision
```

**Why hybrid?**
1. Simpler routing (use standard DefaultRouter)
2. Filters are explicit (no nested URL explosion)
3. Frontend can construct URLs easily
4. Scales better (no N+1 nested routes for many resources)
5. Matches DonorCRM's existing pattern (contacts/{id}/tasks/ are custom views)

### Viewset Implementation

```python
# apps/journals/views.py

from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Journal, JournalContact, JournalStageEvent
from .serializers import (
    JournalSerializer, JournalDetailSerializer,
    JournalMemberSerializer,
    JournalEventSerializer,
    JournalDecisionSerializer
)
from .permissions import IsJournalOwnerOrReadOnly, IsJournalMemberOwnerOrReadOnly
from .filters import JournalFilterSet, JournalMemberFilterSet


class JournalViewSet(viewsets.ModelViewSet):
    """
    Journal CRUD and related actions.
    """
    serializer_class = JournalSerializer
    permission_classes = [permissions.IsAuthenticated, IsJournalOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JournalFilterSet
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'goal_deadline']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user

        # Staff see only their own journals; admins see all
        if user.role == 'admin':
            qs = Journal.objects.all()
        else:
            qs = Journal.objects.filter(owner=user)

        return qs.prefetch_related('members__contact')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return JournalDetailSerializer
        return JournalSerializer

    def perform_create(self, serializer):
        """Set owner to current user."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        GET /journals/{id}/members/ — list contacts in this journal.
        Alternative: GET /journal-members/?journal={id}
        """
        journal = self.get_object()
        members = journal.members.filter(is_active=True)

        serializer = JournalMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def decisions(self, request, pk=None):
        """GET /journals/{id}/decisions/ — current decisions for all contacts."""
        journal = self.get_object()
        members = journal.members.filter(is_active=True)

        decisions = [
            {
                'journal_contact_id': jc.id,
                'contact_id': jc.contact.id,
                'contact_name': jc.contact.full_name,
                'decision': JournalDecisionSerializer(
                    jc.decision_current
                ).data
            }
            for jc in members.select_related('contact', 'decision_current')
        ]

        return Response(decisions)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """GET /journals/{id}/report/ — aggregated stats for dashboard."""
        journal = self.get_object()
        # Implement report aggregation here (see Pattern 6)
        return Response({
            'total_contacts': journal.members.filter(is_active=True).count(),
            'decisions_made': journal.members.filter(
                decision_current__status__in=['committed', 'declined']
            ).count(),
            # ... more aggregations
        })


class JournalMemberViewSet(viewsets.ModelViewSet):
    """
    Journal membership (JournalContact) CRUD.
    """
    serializer_class = JournalMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsJournalMemberOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalMemberFilterSet  # journal=X, contact=Y, is_active

    def get_queryset(self):
        user = self.request.user

        # Filter to journals the user owns
        if user.role == 'admin':
            qs = JournalContact.objects.all()
        else:
            qs = JournalContact.objects.filter(journal__owner=user)

        return qs.select_related('journal', 'contact', 'decision_current')

    def perform_create(self, serializer):
        """Set added_by to current user."""
        serializer.save(added_by=self.request.user)

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Remove a contact from a journal (soft delete)."""
        member = self.get_object()
        member.is_active = False
        member.archived_at = timezone.now()
        member.save()
        return Response({'detail': 'Contact removed from journal.'})


class JournalEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only: view stage events.
    """
    serializer_class = JournalEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsJournalMemberOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['journal_contact', 'stage', 'event_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user

        # Filter to journals the user owns
        if user.role == 'admin':
            qs = JournalStageEvent.objects.all()
        else:
            qs = JournalStageEvent.objects.filter(
                journal_contact__journal__owner=user
            )

        return qs.select_related('journal_contact', 'triggered_by')
```

---

## Pattern 6: Report/Analytics Queries with ORM Aggregation

### The Challenge

Dashboard needs to show:
- Total contacts in journal
- Breakdown by stage (how many in Contact vs Meet vs Close?)
- Breakdown by decision (how many committed vs undecided?)
- Time in each stage (average, median)
- Revenue (total committed, by cadence)

### Solution: Annotate + Aggregate at Querystring Level

```python
# apps/journals/services.py

from django.db.models import Count, Q, Case, When, DecimalField, F, Sum
from django.db.models.functions import Coalesce

class JournalReportService:
    """
    Aggregation queries for dashboards.
    All use select_related/prefetch_related to avoid N+1.
    """

    @staticmethod
    def get_pipeline_breakdown(journal):
        """
        Stage distribution: how many contacts in each stage?
        Returns: {
            'contact': 5,
            'meet': 3,
            'close': 2,
            'decision': 7,
            'thank': 1,
            'next_steps': 0
        }
        """
        stages = ['contact', 'meet', 'close', 'decision', 'thank', 'next_steps']

        members = journal.members.filter(is_active=True).select_related('stage_state')

        breakdown = {}
        for stage in stages:
            count = sum(
                1 for m in members
                if m.stage_state and m.stage_state.current_stage == stage
            )
            breakdown[stage] = count

        # Better: use aggregation
        from django.db.models import Count, Case, When, Value

        breakdown = journal.members.filter(
            is_active=True
        ).values('stage_state__current_stage').annotate(
            count=Count('id')
        )
        # Returns: [{'stage_state__current_stage': 'contact', 'count': 5}, ...]

        return {
            row['stage_state__current_stage'] or 'unknown': row['count']
            for row in breakdown
        }

    @staticmethod
    def get_decision_breakdown(journal):
        """
        Decision distribution: undecided, considering, committed, declined
        """
        decisions = journal.members.filter(
            is_active=True
        ).values('decision_current__status').annotate(
            count=Count('id'),
            total_amount=Coalesce(
                Sum('decision_current__amount_cents'), 0
            )
        )

        return {
            row['decision_current__status'] or 'unknown': {
                'count': row['count'],
                'total_amount_cents': row['total_amount']
            }
            for row in decisions
        }

    @staticmethod
    def get_revenue_by_cadence(journal):
        """
        Total committed revenue, broken down by cadence (monthly, annual, etc)
        """
        committed = journal.members.filter(
            is_active=True,
            decision_current__status='committed'
        ).values('decision_current__cadence').annotate(
            count=Count('id'),
            total_amount=Sum('decision_current__amount_cents')
        )

        return {
            row['decision_current__cadence'] or 'unknown': {
                'count': row['count'],
                'total_amount_cents': row['total_amount'] or 0
            }
            for row in committed
        }

    @staticmethod
    def get_time_in_stage_metrics(journal):
        """
        Average/median time spent in each stage.
        Uses EventTimestamp to calculate duration.
        """
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from datetime import datetime

        stages = ['contact', 'meet', 'close', 'decision', 'thank', 'next_steps']

        metrics = {}
        for stage in stages:
            # For each member, find when they entered and exited this stage
            # This requires more complex query with LAG/LEAD or Python logic

            # Simplified: use created_at of stage_state
            # (In production, calculate from event timestamps)
            events = JournalStageEvent.objects.filter(
                journal_contact__journal=journal,
                stage=stage,
                event_type='stage_entered'
            ).values('journal_contact__contact__id').annotate(
                entered_at=Min('created_at'),
                exited_at=Max('created_at')  # Simplified
            )

            metrics[stage] = {
                'count': len(events),
                # Average duration calculation would go here
            }

        return metrics
```

### In Views: Return Aggregated Data

```python
# In JournalViewSet

@action(detail=True, methods=['get'])
def report(self, request, pk=None):
    """GET /journals/{id}/report/ — dashboard data."""
    journal = self.get_object()

    # All aggregation in one response
    return Response({
        'journal': JournalDetailSerializer(journal).data,
        'pipeline': JournalReportService.get_pipeline_breakdown(journal),
        'decisions': JournalReportService.get_decision_breakdown(journal),
        'revenue': JournalReportService.get_revenue_by_cadence(journal),
        'time_in_stage': JournalReportService.get_time_in_stage_metrics(journal),
    })
```

### Key Aggregation Patterns

**Count by category:**
```python
qs.values('stage').annotate(count=Count('id'))
```

**Sum with condition:**
```python
qs.filter(decision_current__status='committed').annotate(
    total=Sum('decision_current__amount_cents')
)
```

**Multiple aggregates:**
```python
qs.annotate(
    count=Count('id'),
    avg_amount=Avg('decision_current__amount_cents'),
    max_amount=Max('decision_current__amount_cents')
)
```

---

## Pattern 7: Sequential Pipeline with Flexible Ordering

### The Model

6-stage pipeline: Contact → Meet → Close → Decision → Thank → Next Steps

**Constraints:**
- Normal progression: must go through stages in order
- Flexible: can skip or revisit stages (with warnings, not blocks)
- Warnings are informational, not blocking

### Implementation

```python
# apps/journals/models.py

class JournalContactStageState(TimeStampedModel):
    # ... (from Pattern 2)

    current_stage = models.CharField(max_length=20)
    skipped = models.BooleanField(default=False)  # Is this stage skipped?
    revisited = models.BooleanField(default=False)  # Back to this stage?
    is_blocked = models.BooleanField(default=False)  # Admin-set flag

# apps/journals/services.py

STAGE_ORDER = {
    'contact': 1,
    'meet': 2,
    'close': 3,
    'decision': 4,
    'thank': 5,
    'next_steps': 6,
}

def move_to_stage(journal_contact, new_stage, user, allow_backward=False):
    """
    Move contact to a new stage, returning (success, warning).

    Warnings:
    - "Revisiting Contact stage" (backward movement)
    - "Skipping Meet and Close stages" (more than 1 ahead)

    Never blocks, always succeeds.
    """
    state = journal_contact.stage_state
    old_stage = state.current_stage
    old_order = STAGE_ORDER[old_stage]
    new_order = STAGE_ORDER[new_stage]

    warnings = []

    # Check backward (revisit)
    if new_order < old_order:
        warnings.append(
            f'Revisiting {new_stage} (moved back from {old_stage})'
        )
        state.revisited = True

    # Check skipping
    if new_order > old_order + 1:
        skipped_stages = [
            s for s, o in STAGE_ORDER.items()
            if old_order < o < new_order
        ]
        warnings.append(
            f'Skipping stages: {", ".join(skipped_stages)}'
        )
        state.skipped = True

    # Update state and log event
    state.current_stage = new_stage
    state.last_activity_at = timezone.now()
    state.save()

    # Log event
    event_type = (
        'stage_revisited' if new_order < old_order else
        'stage_skipped' if new_order > old_order + 1 else
        'stage_entered'
    )

    JournalStageEvent.objects.create(
        journal_contact=journal_contact,
        stage=new_stage,
        event_type=event_type,
        triggered_by=user,
        notes=f'Moved from {old_stage} to {new_stage}',
        metadata={'skipped_stages': [
            s for s, o in STAGE_ORDER.items()
            if old_order < o < new_order
        ] if new_order > old_order + 1 else []}
    )

    return (True, warnings)
```

---

## Pattern 8: Permission Inheritance for Nested Resources

### The Challenge

If a user owns journal A, they can see:
- Journal A
- All contacts in journal A
- All events for those contacts
- All decisions for those contacts

But NOT contact B if it's in someone else's journal.

### Solution: Permission Classes + Queryset Filtering

```python
# apps/journals/permissions.py

from rest_framework import permissions

class IsJournalOwnerOrReadOnly(permissions.BasePermission):
    """
    Journal owner can edit; others can only read.
    Admins can do anything.
    """

    def has_permission(self, request, view):
        # All authenticated users can list/create
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write access: must be owner or admin
        if request.user.role == 'admin':
            return True
        return obj.owner == request.user


class IsJournalMemberOwnerOrReadOnly(permissions.BasePermission):
    """
    Can view/edit journal member if user owns the journal.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # obj is JournalContact or JournalStageEvent
        journal = obj.journal_contact.journal if hasattr(obj, 'journal_contact') else obj.journal

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.role == 'admin':
            return True
        return journal.owner == request.user
```

### In Viewsets: Filter Queryset by Owner

```python
# apps/journals/views.py

class JournalViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return Journal.objects.all()

        # Staff see only their own
        return Journal.objects.filter(owner=user)


class JournalMemberViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return JournalContact.objects.all()

        # Staff see members of their journals only
        return JournalContact.objects.filter(journal__owner=user)


class JournalEventViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            return JournalStageEvent.objects.all()

        # Staff see events from their journals
        return JournalStageEvent.objects.filter(
            journal_contact__journal__owner=user
        )
```

**Pattern:** Always filter at the queryset level, then use permission classes for edge cases.

---

## Pattern 9: Linking to Existing Task System

### The Problem

Journal workflows naturally generate tasks (e.g., "Call Jane after decision"). The existing Task model should be linkable to journals.

### Solution: FK to Journal on Task

```python
# Add to apps/tasks/models.py

class Task(TimeStampedModel):
    # Existing fields...
    owner = models.ForeignKey(...)
    contact = models.ForeignKey(...)

    # NEW: Optional link to journal
    journal = models.ForeignKey(
        'journals.Journal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text='Journal this task belongs to (optional)'
    )

    class Meta:
        db_table = 'tasks'
        # Add journal to indexes
        indexes = [
            models.Index(fields=['owner', 'status', 'due_date']),
            models.Index(fields=['journal', 'status']),  # NEW
        ]
```

### Migrations

```bash
python manage.py makemigrations tasks
python manage.py migrate
```

### Usage in Journal Views

```python
# When creating a task in the context of a journal:

task = Task.objects.create(
    owner=request.user,
    contact=journal_contact.contact,
    journal=journal,
    title='Follow up on decision',
    due_date=date.today() + timedelta(days=7)
)

# In task list, filter by journal:
journal.tasks.filter(status='pending')
```

### Why FK Instead of M2M

- Tasks → Journal is one-to-many (one task per journal context)
- M2M would allow task in multiple journals (overengineering)
- FK with null=True keeps tasks optional in journal system

---

## Anti-Patterns to Avoid

### 1. Full Event Replay for Current State

**Bad:**
```python
# For every query, compute state from scratch
def get_current_stage(journal_contact):
    events = JournalStageEvent.objects.filter(
        journal_contact=journal_contact
    ).order_by('-created_at')
    return events.first().stage if events else None
```

**Good:**
```python
# Query denormalized state (instant)
return journal_contact.stage_state.current_stage
```

**Why:** Event replay is O(N) in event count. Denormalized state is O(1).

### 2. Nested Serializers Without Limits

**Bad:**
```python
class JournalSerializer(serializers.ModelSerializer):
    members = JournalMemberSerializer(many=True)
    decision_history = JournalDecisionHistorySerializer(many=True)
    stage_events = JournalStageEventSerializer(many=True)

    class Meta:
        fields = '__all__'
```

**Good:**
```python
class JournalDetailSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()

    def get_members_count(self, obj):
        return obj.members.filter(is_active=True).count()

    class Meta:
        fields = ['id', 'name', 'members_count', ...]
```

**Why:** Nested serializers with many=True cause N+1 queries and bloated responses.

### 3. Updating History Directly

**Bad:**
```python
# User sees history endpoint and POSTs to it
PUT /journal-decision-history/{id}/
{'status': 'committed', 'amount_cents': 500000}
```

**Good:**
```python
# Update current; service creates history
PUT /journal-members/{id}/
{'status': 'committed', 'amount_cents': 500000}

# Service does:
# 1. Create JournalDecisionHistory (copy old values)
# 2. Update JournalDecisionCurrent
```

**Why:** History should be immutable. Service layer enforces single entry point.

### 4. Querying Across Unindexed Fields

**Bad:**
```python
# Slow: no index on (journal, is_active, decision_status)
members = JournalContact.objects.filter(
    journal=journal,
    is_active=True,
    decision_current__status='committed'
).count()
```

**Good:**
```python
# Index on (journal, is_active) + filter in Python
members = journal.members.filter(is_active=True).select_related(
    'decision_current'
).count()

# Or add composite index:
class Meta:
    indexes = [
        models.Index(fields=['journal', 'is_active', 'decision_current']),
    ]
```

### 5. Over-Normalizing Pipeline State

**Bad:**
```python
# Separate tables for each stage, joined together
class ContactStage(TimeStampedModel):
    stage = models.CharField(choices=STAGES)
    # Broken: this forces nullable fields for non-current stages
```

**Good:**
```python
# One JournalContactStageState per (journal, contact)
class JournalContactStageState(TimeStampedModel):
    current_stage = CharField()  # Always has a value
```

---

## Summary: Architecture Decision Matrix

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Event Storage** | Append-only log + denormalized state | Performance (read-heavy), audit trail |
| **Decision History** | Dual tables (Current + History) | Immutable audit, mutable current access |
| **Many-to-Many** | Explicit through model (JournalContact) | Extra fields (added_by, notes, is_active) |
| **App Structure** | Single `journals` app | High cohesion, follows DonorCRM pattern |
| **API Design** | Flat endpoints + query params | Simplicity, scales better than nested routes |
| **Permissions** | Queryset filtering + custom classes | Owner-scoped, admin visibility |
| **Reports** | ORM annotate/aggregate at query time | Avoids N+1, database is powerful |
| **State Machine** | Warnings not blocks | Flexible workflow, staff judgment |
| **Task Integration** | FK on Task model | Simple, reuses existing system |

---

## Implementation Checklist

- [ ] Create models: Journal, JournalContact, JournalStageEvent, JournalContactStageState, JournalDecisionCurrent, JournalDecisionHistory
- [ ] Add FK to Task.journal
- [ ] Create serializers (simple, detail, list variants)
- [ ] Create viewsets with filtering and permissions
- [ ] Create custom permission classes
- [ ] Create services.py for business logic
- [ ] Write tests for models, views, permissions
- [ ] Implement report aggregation queries
- [ ] Create migrations
- [ ] Add to INSTALLED_APPS

---

## Sources

- [Django REST Framework Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [Django Model Relationships](https://docs.djangoproject.com/en/4.2/topics/db/models/)
- [Django ORM Aggregation](https://docs.djangoproject.com/en/6.0/topics/db/aggregation/)
- [Event Sourcing in Python](https://eventsourcing.readthedocs.io/)
- [DRF Nested Routers](https://github.com/alanjds/drf-nested-routers)
- [Django Many-to-Many Best Practices](https://www.sankalpjonna.com/learn-django/the-right-way-to-use-a-manytomanyfield-in-django)
- [Django-Simple-History](https://django-simple-history.readthedocs.io/)
- [Django App Organization Best Practices](https://learndjango.com/tutorials/django-best-practices-projects-vs-apps)
- [DRF Custom Permissions](https://testdriven.io/blog/custom-permission-classes-drf/)
