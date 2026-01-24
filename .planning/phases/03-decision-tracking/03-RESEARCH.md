# Phase 3: Decision Tracking - Research

**Researched:** 2026-01-24
**Domain:** Django dual-table pattern for current state + history tracking
**Confidence:** HIGH

## Summary

This phase implements decision tracking with a dual-table pattern: one table for current decision state (mutable, unique per journal+contact) and another for append-only history. The pattern mirrors pledge management but adds temporal tracking for audit compliance.

The research examined Django's transaction.atomic() patterns, history tracking libraries (django-simple-history, django-auditlog), and the existing pledges app which already implements similar cadence normalization and state management. The key technical challenge is ensuring atomic updates: when a decision changes, the system must append to history AND update current state within a single transaction to maintain consistency.

This is a manual history implementation (not django-simple-history) because:
1. The codebase already has custom patterns (JournalStageEvent is append-only)
2. Requirements specify exact fields to track (changed fields, old values)
3. Fine-grained control over what triggers history (not every model save, only decision changes)

**Primary recommendation:** Follow the pledges app pattern for cadence normalization and status management, wrap decision updates in transaction.atomic() blocks, and use DecimalField (not integer cents) to match the existing project's money storage pattern from Phase 1.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django ORM | 4.2.11 | Database layer | Project standard, native transaction support |
| Django transaction.atomic | 4.2.11 | Atomic transactions | Ensures history + update consistency |
| DecimalField | Django built-in | Money storage | Project uses DecimalField throughout (Phase 1 decision) |
| UniqueConstraint | Django 4.2+ | Enforce one current decision | Modern Django constraint API |
| DRF Pagination | Latest | History pagination | PageNumberPagination for 25-record default |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-filter | Latest | Queryset filtering | Filter decision history by date range |
| select_related | Django ORM | N+1 prevention | Load journal_contact relations efficiently |
| JSONField | Django built-in | Track changed fields | Store {field: old_value} mapping in history |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual history | django-simple-history | Manual gives fine control, simpler for this use case, no extra library |
| Manual history | django-auditlog | Same - requirements are specific, manual is cleaner |
| IntegerField (cents) | DecimalField | **DecimalField chosen in Phase 1** - follow existing pattern |
| unique_together | UniqueConstraint | UniqueConstraint is modern Django best practice (recommended since Django 2.2) |

**Installation:**
Not applicable - all dependencies already in project.

## Architecture Patterns

### Recommended Project Structure
```
apps/journals/
├── models.py
│   ├── Decision (current state table)
│   └── DecisionHistory (append-only history table)
├── serializers.py
│   ├── DecisionSerializer (create/update with auto-history)
│   ├── DecisionHistorySerializer (read-only)
├── views.py
│   ├── DecisionListCreateView (CRUD for current decisions)
│   ├── DecisionDetailView (retrieve/update/delete)
│   └── DecisionHistoryListView (paginated history)
└── tests/
    ├── test_decision_models.py (cadence calc, monthly_equivalent)
    └── test_decision_api.py (CRUD, history tracking, atomic updates)
```

### Pattern 1: Dual-Table Current + History
**What:** Two models - Decision (current state, mutable) and DecisionHistory (append-only log)
**When to use:** Audit trail requirements with mutable current state
**Example:**
```python
# Source: Manual implementation based on research
class Decision(TimeStampedModel):
    """Current decision state - one per journal+contact."""
    journal_contact = models.ForeignKey(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='decision'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cadence = models.CharField(max_length=20, choices=DecisionCadence.choices)
    status = models.CharField(max_length=20, choices=DecisionStatus.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['journal_contact'],
                name='unique_decision_per_journal_contact'
            )
        ]

class DecisionHistory(TimeStampedModel):
    """Append-only history of decision changes."""
    decision = models.ForeignKey('Decision', on_delete=models.CASCADE)
    changed_fields = models.JSONField()  # {field: old_value}
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
```

**Key insight:**
- Current table has unique constraint (one decision per journal+contact)
- History table has no constraints, just FK to decision
- Every update creates history record BEFORE updating current

### Pattern 2: Atomic History Transaction
**What:** Wrap history append + current update in transaction.atomic()
**When to use:** Every decision update operation
**Example:**
```python
# Source: Django official docs + research
from django.db import transaction

def update_decision(decision, new_data, user):
    """Update decision with automatic history tracking."""
    with transaction.atomic():
        # 1. Identify changed fields
        changed = {}
        if new_data.get('amount') != decision.amount:
            changed['amount'] = str(decision.amount)
        if new_data.get('cadence') != decision.cadence:
            changed['cadence'] = decision.cadence
        if new_data.get('status') != decision.status:
            changed['status'] = decision.status

        # 2. Create history record if changes exist
        if changed:
            DecisionHistory.objects.create(
                decision=decision,
                changed_fields=changed,
                changed_by=user
            )

        # 3. Update current state
        decision.amount = new_data.get('amount', decision.amount)
        decision.cadence = new_data.get('cadence', decision.cadence)
        decision.status = new_data.get('status', decision.status)
        decision.save()
```

**Warning:** Critical pitfall from STATE.md - "Phase 2: Atomic transaction scope bugs (wrap decision update + history + event creation in single transaction)" - this is actually Phase 3's pitfall, ensure all related operations are inside transaction.atomic().

### Pattern 3: Cadence Normalization
**What:** Calculate monthly_equivalent property for aggregation
**When to use:** Report calculations, goal tracking
**Example:**
```python
# Source: apps/pledges/models.py lines 111-120
class Decision(TimeStampedModel):
    # ... fields ...

    @property
    def monthly_equivalent(self):
        """Calculate monthly equivalent for aggregation."""
        multipliers = {
            DecisionCadence.ONE_TIME: 0,  # One-time excluded from monthly
            DecisionCadence.MONTHLY: 1,
            DecisionCadence.QUARTERLY: 1 / 3,
            DecisionCadence.ANNUAL: 1 / 12,
        }
        return float(self.amount) * multipliers.get(self.cadence, 0)
```

**Note:** Requirements say quarterly → amount/3, annual → amount/12. One-time gifts should be excluded from monthly calculations (or divided by campaign length).

### Pattern 4: UniqueConstraint vs unique_together
**What:** Use Meta.constraints with UniqueConstraint instead of unique_together
**When to use:** Enforcing one current decision per journal+contact
**Example:**
```python
# Source: Django 5.2 official documentation
class Decision(TimeStampedModel):
    journal_contact = models.ForeignKey('JournalContact', ...)

    class Meta:
        db_table = 'journal_decisions'
        constraints = [
            models.UniqueConstraint(
                fields=['journal_contact'],
                name='unique_decision_per_journal_contact'
            )
        ]
```

**Why UniqueConstraint:**
- Recommended Django best practice since 2.2
- Allows custom constraint names (better migrations)
- Supports conditional constraints (future flexibility)
- More explicit than unique_together

### Pattern 5: Pagination for History
**What:** Use DRF's PageNumberPagination for decision history
**When to use:** Listing decision changes (default 25 records)
**Example:**
```python
# Source: DRF official documentation + existing views pattern
from rest_framework.pagination import PageNumberPagination

class DecisionHistoryPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

class DecisionHistoryListView(generics.ListAPIView):
    serializer_class = DecisionHistorySerializer
    pagination_class = DecisionHistoryPagination

    def get_queryset(self):
        # Filter by decision or journal_contact
        return DecisionHistory.objects.select_related(
            'decision',
            'decision__journal_contact',
            'changed_by'
        ).order_by('-created_at')
```

### Anti-Patterns to Avoid

- **Saving without transaction.atomic():** Decision updates must be atomic - history + current state together or neither
- **N+1 queries in history views:** Always use select_related for decision, journal_contact, changed_by
- **Triggering history on every save():** Only create history when fields actually change (check changed_fields)
- **Using IntegerField for cents:** Phase 1 decided on DecimalField - follow that pattern
- **unique_together instead of UniqueConstraint:** Use modern constraint API

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full model versioning | Custom history tracking for all fields | django-simple-history | But we're NOT using it - manual is simpler for this specific use case |
| Transaction management | Try/except with manual rollback | transaction.atomic() context manager | Django handles rollback automatically, cleaner code |
| Monthly equivalents | Manual if/else chains | Dictionary-based multipliers (pledge pattern) | More maintainable, easy to add cadences |
| Pagination logic | Custom offset/limit math | PageNumberPagination | Handles edge cases, standardized response format |

**Key insight:** For this phase, manual history is appropriate because:
1. We only track decision changes, not all model saves
2. Requirements specify exact fields to store (changed_fields, old values)
3. Fine-grained control over when history is created
4. Avoids extra library dependency
5. Simpler to reason about than django-simple-history's metaclass magic

## Common Pitfalls

### Pitfall 1: Atomic Transaction Scope
**What goes wrong:** History record created but decision update fails, or vice versa - data inconsistency
**Why it happens:** Not wrapping both operations in transaction.atomic(), or transaction scope too narrow
**How to avoid:**
- Always use transaction.atomic() context manager for decision updates
- Put history creation AND current state update inside same atomic block
- Include any related operations (event logging) in same transaction if they must be consistent
**Warning signs:**
- DecisionHistory records without corresponding decision updates
- Decision updated but no history record exists
- IntegrityError on concurrent updates

### Pitfall 2: Changed Fields Detection Logic
**What goes wrong:** History created on every save even when nothing changed, or changes not detected
**Why it happens:** Not comparing old vs new values before creating history
**How to avoid:**
- Load current values before update
- Compare new_data with existing decision attributes
- Only create history if changed dict is non-empty
- Use str() conversion for Decimal comparison consistency
**Warning signs:**
- Bloated history table with duplicate entries
- "Changed" records with empty changed_fields
- Missing history when values actually changed

### Pitfall 3: Monthly Equivalent for One-Time Gifts
**What goes wrong:** One-time gifts skew monthly calculations
**Why it happens:** Multiplying one-time amount by 1 instead of excluding or amortizing
**How to avoid:**
- Set multiplier to 0 for one-time (exclude from monthly aggregation)
- OR divide by campaign length if including (requires campaign duration field)
- Document the calculation logic clearly
**Warning signs:**
- Goal progress jumps unexpectedly after one-time gift
- Monthly totals don't match pledge patterns

### Pitfall 4: UniqueConstraint Violation Handling
**What goes wrong:** 500 error when creating duplicate decision instead of user-friendly 400
**Why it happens:** IntegrityError not caught and converted to validation error
**How to avoid:**
- Use get_or_create for decision creation
- OR catch IntegrityError in create view and return 400 with clear message
- Enforce constraint at serializer level before database hit
**Warning signs:**
- 500 errors in logs for duplicate decision attempts
- Users see generic error instead of "decision already exists"

### Pitfall 5: History Pagination Without select_related
**What goes wrong:** N+1 query problem loading history - one query per history record for related objects
**Why it happens:** Accessing decision.journal_contact.contact without prefetching
**How to avoid:**
- Always use select_related('decision', 'decision__journal_contact', 'changed_by') in history queryset
- Verify with Django debug toolbar or assertNumQueries in tests
**Warning signs:**
- Slow history list API (>100ms for 25 records)
- Django debug toolbar shows N queries for N history records
- Database connection pool exhaustion under load

## Code Examples

Verified patterns from official sources and existing codebase:

### Decision Model with Cadence Choices
```python
# Source: Combining apps/pledges/models.py pattern + research
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from apps.core.models import TimeStampedModel

class DecisionCadence(models.TextChoices):
    """Pledge cadence options."""
    ONE_TIME = 'one_time', 'One-Time'
    MONTHLY = 'monthly', 'Monthly'
    QUARTERLY = 'quarterly', 'Quarterly'
    ANNUAL = 'annual', 'Annual'

class DecisionStatus(models.TextChoices):
    """Decision status tracking."""
    PENDING = 'pending', 'Pending'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    DECLINED = 'declined', 'Declined'

class Decision(TimeStampedModel):
    """Current decision state for a contact in a journal."""
    journal_contact = models.ForeignKey(
        'JournalContact',
        on_delete=models.CASCADE,
        related_name='decision'
    )
    amount = models.DecimalField(
        'amount',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Pledged amount'
    )
    cadence = models.CharField(
        'cadence',
        max_length=20,
        choices=DecisionCadence.choices,
        default=DecisionCadence.MONTHLY
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PENDING,
        db_index=True
    )

    class Meta:
        db_table = 'journal_decisions'
        verbose_name = 'journal decision'
        verbose_name_plural = 'journal decisions'
        constraints = [
            models.UniqueConstraint(
                fields=['journal_contact'],
                name='unique_decision_per_journal_contact'
            )
        ]

    @property
    def monthly_equivalent(self):
        """Calculate monthly equivalent for aggregation."""
        multipliers = {
            DecisionCadence.ONE_TIME: 0,  # Exclude from monthly
            DecisionCadence.MONTHLY: 1,
            DecisionCadence.QUARTERLY: Decimal('0.333333'),  # 1/3
            DecisionCadence.ANNUAL: Decimal('0.083333'),  # 1/12
        }
        return self.amount * multipliers.get(self.cadence, 0)
```

### Decision History Model
```python
# Source: Manual implementation based on research
class DecisionHistory(TimeStampedModel):
    """Append-only history of decision changes."""
    decision = models.ForeignKey(
        'Decision',
        on_delete=models.CASCADE,
        related_name='history',
        db_index=True
    )
    changed_fields = models.JSONField(
        'changed fields',
        help_text='Mapping of field names to old values before change'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='decision_changes',
        help_text='User who made the change'
    )

    class Meta:
        db_table = 'journal_decision_history'
        verbose_name = 'decision history'
        verbose_name_plural = 'decision history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['decision', '-created_at']),
        ]
```

### Atomic Update with History
```python
# Source: Django transaction.atomic pattern + research
from django.db import transaction

class DecisionSerializer(serializers.ModelSerializer):
    # ... fields ...

    def update(self, instance, validated_data):
        """Update decision with automatic history tracking."""
        request = self.context.get('request')
        user = request.user if request else None

        with transaction.atomic():
            # Detect changed fields
            changed = {}
            for field in ['amount', 'cadence', 'status']:
                new_value = validated_data.get(field)
                if new_value and new_value != getattr(instance, field):
                    # Store old value (convert Decimal to string for JSON)
                    old_value = getattr(instance, field)
                    changed[field] = str(old_value) if isinstance(old_value, Decimal) else old_value

            # Create history record if changes exist
            if changed:
                DecisionHistory.objects.create(
                    decision=instance,
                    changed_fields=changed,
                    changed_by=user
                )

            # Update current state
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            return instance
```

### History List View with Pagination
```python
# Source: DRF pagination + existing view patterns
from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination

class DecisionHistoryPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

class DecisionHistoryListView(generics.ListAPIView):
    """
    GET: List decision history with pagination (default 25 records)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DecisionHistorySerializer
    pagination_class = DecisionHistoryPagination

    def get_queryset(self):
        user = self.request.user

        # Base queryset with efficient joins
        queryset = DecisionHistory.objects.select_related(
            'decision',
            'decision__journal_contact',
            'decision__journal_contact__journal',
            'decision__journal_contact__contact',
            'changed_by'
        )

        # Filter by ownership (unless admin)
        if user.role != 'admin':
            queryset = queryset.filter(
                decision__journal_contact__journal__owner=user
            )

        # Optional filter by decision or journal_contact
        decision_id = self.request.query_params.get('decision_id')
        if decision_id:
            queryset = queryset.filter(decision_id=decision_id)

        journal_contact_id = self.request.query_params.get('journal_contact_id')
        if journal_contact_id:
            queryset = queryset.filter(
                decision__journal_contact_id=journal_contact_id
            )

        return queryset.order_by('-created_at')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| unique_together | UniqueConstraint | Django 2.2 (2019) | Better constraint naming, conditional support |
| Manual transaction handling | transaction.atomic() | Django 1.6 (2013) | Automatic rollback, cleaner code |
| IntegerField for money | DecimalField | Industry standard | Avoid floating point, match accounting precision |
| django-reversion | django-simple-history | ~2015 | Simpler API, better maintained |

**Deprecated/outdated:**
- **unique_together**: Still works but UniqueConstraint is preferred (Django docs recommend since 2.2)
- **Manual commit/rollback**: Use transaction.atomic() instead
- **Storing money as floats**: Always use Decimal or integer cents

## Open Questions

Things that couldn't be fully resolved:

1. **One-time gift monthly normalization**
   - What we know: Requirements say "normalize to monthly equivalent for aggregation"
   - What's unclear: Should one-time gifts be included (divided by campaign length) or excluded?
   - Recommendation: Exclude from monthly (multiplier = 0) but include in total goal tracking. Revisit if product owner wants different behavior.

2. **History retention policy**
   - What we know: History is append-only, requirements don't specify retention
   - What's unclear: Should old history be archived/deleted after X years?
   - Recommendation: Keep all history (storage is cheap), add index on created_at for efficient queries. Implement archival only if table grows beyond 1M rows.

3. **Changed fields granularity**
   - What we know: Store {field: old_value} mapping
   - What's unclear: Should we store new_value too, or just old? Should we track who triggered the change (could be system vs user)?
   - Recommendation: Store old_value only (new value is in current record), track changed_by user. This matches audit log best practices.

## Sources

### Primary (HIGH confidence)
- [Django Database Transactions Official Docs](https://docs.djangoproject.com/en/6.0/topics/db/transactions/) - transaction.atomic() patterns
- [Django Constraints Reference](https://docs.djangoproject.com/en/5.2/ref/models/constraints/) - UniqueConstraint API
- [DRF Pagination Guide](https://www.django-rest-framework.org/api-guide/pagination/) - PageNumberPagination configuration
- Existing codebase: apps/pledges/models.py (lines 111-120) - monthly_equivalent pattern
- Existing codebase: apps/journals/models.py - TimeStampedModel pattern
- Phase 1 research: 01-RESEARCH.md - established project patterns

### Secondary (MEDIUM confidence)
- [Django Simple History Docs](https://django-simple-history.readthedocs.io/) - Understanding automatic history tracking (not using, but researched)
- [Django Audit Logging Article](https://medium.com/@mariliabontempo/django-audit-logging-the-best-libraries-for-tracking-model-changes-with-postgresql-2c7396564e97) - Ecosystem overview
- [DecimalField Best Practices](https://dev.to/koladev/django-tip-use-decimalfield-for-money-3f63) - Money storage recommendations
- [Keeping Accurate Amounts in Django](https://deepintodjango.com/keeping-accurate-amounts-in-django-with-currencyfield) - Currency handling patterns

### Tertiary (LOW confidence)
- WebSearch results for "Django dual-table pattern" - General patterns discussion
- WebSearch results for "Django atomic transaction" - Community usage examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, Django/DRF official features
- Architecture: HIGH - Patterns verified in existing codebase (pledges, journals)
- Pitfalls: HIGH - Atomic transaction scope explicitly called out in STATE.md, other pitfalls from DRF/Django best practices

**Research date:** 2026-01-24
**Valid until:** 90 days (stable Django/DRF patterns, not fast-moving)

**Key decision reference:**
- Phase 1 Decision 01-01: "DecimalField for money storage - Changed from integer cents to DecimalField (follows existing pledges/donations pattern)"
- This phase MUST use DecimalField, not integer cents as originally specified in requirements

**Requirements coverage:**
- JRN-07: Decision Current State - Dual-table pattern with unique constraint
- JRN-08: Decision History - Append-only history with changed_fields JSON
- JRN-09: Decision Cadence Support - Monthly equivalent calculation (pledges pattern)
