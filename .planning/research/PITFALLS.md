# Domain Pitfalls: Pipeline/Stage Tracking with Event Sourcing

**Domain:** Fundraising pipeline kanban with event-sourced stages, grid UI, decision tracking
**Researched:** 2026-01-24
**Context:** Django/DRF + React, 100+ contacts × 7 columns grid, append-only events, decision current+history

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: N+1 Queries from Derived Current State

**What goes wrong:** Computing "current stage" from event history for each contact independently creates N+1 queries. With 100 contacts, this becomes 1 query for contacts + 100 queries for stage events = crushing performance.

**Why it happens:** Event sourcing requires replaying events to compute current state. Naive implementation queries events per contact inside a loop or property getter. Django ORM makes this easy to do accidentally with `contact.current_stage` as a property that hits the database.

**Consequences:**
- Grid page load times balloon from 200ms to 5+ seconds
- Database connection pool exhaustion under concurrent users
- Server timeouts on grids with 200+ contacts

**Prevention:**
```python
# BAD - N+1 queries
contacts = Contact.objects.filter(journal=journal)
for contact in contacts:
    current_stage = contact.stage_events.latest('created_at').stage  # Query per contact

# GOOD - Prefetch with subquery
from django.db.models import OuterRef, Subquery

latest_stage_events = StageEvent.objects.filter(
    contact=OuterRef('pk'),
    journal=journal
).order_by('-created_at')

contacts = Contact.objects.filter(journal=journal).annotate(
    current_stage=Subquery(latest_stage_events.values('stage')[:1])
).prefetch_related(
    Prefetch('stage_events', queryset=StageEvent.objects.filter(journal=journal))
)
```

**Detection:**
- Django Debug Toolbar showing >50 queries for a single grid page
- `django.db.connection.queries` list growing linearly with contact count
- Slow query logs showing repeated similar SELECT statements

**Phase:** Phase 1 (Data Model + Basic Grid) — must design queries correctly from start

**Sources:**
- [Django select_related and prefetch_related](https://betterprogramming.pub/django-select-related-and-prefetch-related-f23043fd635d)
- [Optimizing Django Queries](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)

---

### Pitfall 2: Atomic Transaction Scope Confusion for Multi-Model Writes

**What goes wrong:** Decision updates must atomically write to Decision (current), DecisionHistory, and StageEvent. Using `transaction.atomic()` incorrectly leads to partial writes where DecisionHistory saves but StageEvent fails, leaving inconsistent state.

**Why it happens:** Django's `transaction.atomic()` doesn't roll back model instance state in memory, only database writes. Developers assume atomic blocks guarantee consistency but don't handle exceptions properly or use nested atomics incorrectly.

**Consequences:**
- Decision shows "Committed $100/month" but no corresponding stage event exists
- Decision history table has orphaned records after failed saves
- User sees success message but data is incomplete
- Debugging requires manual SQL to find inconsistencies

**Prevention:**
```python
# BAD - No transaction boundary
def update_decision(contact, journal, amount, cadence):
    decision = Decision.objects.get(contact=contact, journal=journal)
    decision.amount = amount
    decision.cadence = cadence
    decision.save()  # If this succeeds but next fails, partial write

    DecisionHistory.objects.create(
        decision=decision,
        amount=amount,
        cadence=cadence
    )

    StageEvent.objects.create(
        contact=contact,
        journal=journal,
        stage='DECISION',
        event_type='decision_updated'
    )  # If this fails, decision saved but no event

# GOOD - Atomic with proper exception handling
from django.db import transaction

@transaction.atomic
def update_decision(contact, journal, amount, cadence):
    # All-or-nothing: if any save() fails, entire transaction rolls back
    decision = Decision.objects.select_for_update().get(
        contact=contact,
        journal=journal
    )
    decision.amount = amount
    decision.cadence = cadence
    decision.save()

    DecisionHistory.objects.create(
        decision=decision,
        amount=amount,
        cadence=cadence,
        changed_at=timezone.now()
    )

    StageEvent.objects.create(
        contact=contact,
        journal=journal,
        stage='DECISION',
        event_type='decision_updated',
        metadata={'amount': amount, 'cadence': cadence}
    )
    # Transaction commits only if all three succeed
```

**Detection:**
- Count mismatches: `Decision.objects.count()` != `DecisionHistory.objects.count()`
- Missing stage events for decision changes in audit log
- IntegrityError logs showing constraint violations mid-transaction

**Phase:** Phase 2 (Decision Tracking) — design transaction boundaries before implementing updates

**Caveat:** Never catch exceptions inside `@transaction.atomic` block without re-raising. Django won't rollback if you swallow the exception.

**Sources:**
- [Django's transaction.atomic()](https://charemza.name/blog/posts/django/postgres/transactions/not-as-atomic-as-you-may-think/)
- [The trouble with transaction.atomic](https://seddonym.me/2020/11/19/trouble-atomic/)
- [Django atomic transactions](https://medium.com/@shivanikakrecha/transaction-atomic-in-django-87b787ead793)

---

### Pitfall 3: Event Replay Performance Without Snapshots

**What goes wrong:** Replaying 1000+ events to compute "current stage" for a contact takes 500ms+. Multiply by 100 contacts and grid page becomes unusable. Event sourcing systems without snapshot strategy don't scale past small datasets.

**Why it happens:** Pure event sourcing design says "replay all events to get current state." Works great with 10 events per contact. Breaks down with active contacts accumulating hundreds of stage transitions over months.

**Consequences:**
- Grid rendering hangs browser for 10+ seconds
- Database CPU spikes as replay queries execute
- Older journals become slower than recent ones (more events accumulated)
- Report generation times out

**Prevention:**
```python
# Strategy 1: Denormalize current state (recommended for this use case)
class JournalContact(models.Model):
    """Through table for Contact-Journal relationship"""
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)

    # Denormalized current state - updated on every stage event
    current_stage = models.CharField(max_length=50, default='CONTACT')
    last_stage_change = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['contact', 'journal']]

# Update current_stage whenever StageEvent is created
@receiver(post_save, sender=StageEvent)
def update_current_stage(sender, instance, created, **kwargs):
    if created:
        JournalContact.objects.filter(
            contact=instance.contact,
            journal=instance.journal
        ).update(
            current_stage=instance.stage,
            last_stage_change=instance.created_at
        )

# Strategy 2: Periodic snapshots (if pure event sourcing required)
class StageSnapshot(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    current_stage = models.CharField(max_length=50)
    snapshot_at = models.DateTimeField(auto_now_add=True)
    event_count = models.IntegerField()  # How many events replayed to create this

# Create snapshot every 100 events or weekly
def get_current_stage(contact, journal):
    latest_snapshot = StageSnapshot.objects.filter(
        contact=contact, journal=journal
    ).order_by('-snapshot_at').first()

    if latest_snapshot:
        # Replay only events after snapshot
        events = StageEvent.objects.filter(
            contact=contact,
            journal=journal,
            created_at__gt=latest_snapshot.snapshot_at
        ).order_by('created_at')
    else:
        # No snapshot, replay all events
        events = StageEvent.objects.filter(
            contact=contact,
            journal=journal
        ).order_by('created_at')

    current_stage = latest_snapshot.current_stage if latest_snapshot else 'CONTACT'
    for event in events:
        current_stage = event.stage  # Simplified - actual replay logic here

    return current_stage
```

**Detection:**
- `select * from stage_events` queries taking >100ms
- Grid component shows loading spinner for >2 seconds
- Browser profiler shows JavaScript replay loops consuming CPU

**Phase:** Phase 1 (Data Model) — choose denormalization vs snapshot strategy before writing event models

**Recommendation:** Denormalize current_stage in JournalContact through table. Event log remains append-only for audit, but current state is O(1) lookup. Snapshots add complexity without benefit for this scale (100s of contacts, not millions).

**Sources:**
- [Snapshot Strategies: Optimizing Event Replays](https://dev.to/alex_aslam/snapshot-strategies-optimizing-event-replays-36oo)
- [Optimizing Event Replays](https://docs.eventsourcingdb.io/best-practices/optimizing-event-replays/)
- [The Performance Factor in Event Sourcing](https://patchlevel.de/blog/the-performance-factor-in-event-sourcing)

---

### Pitfall 4: React Grid Cell Re-render Cascade

**What goes wrong:** Updating one cell (e.g., marking stage complete) triggers re-render of entire 100-row grid because cell components take entire row object as prop. Browser freezes for 2-3 seconds on every interaction.

**Why it happens:** Cell components receive `rowData` prop containing all contact fields. When any field changes (even unrelated to this cell), React sees prop changed and re-renders. Multiply by 100 contacts × 7 columns = 700 cell re-renders for a single stage update.

**Consequences:**
- UI feels sluggish on every click
- Optimistic updates lag 2-3 seconds before showing
- Mobile devices become unusable (lower CPU)
- User abandons feature thinking it's broken

**Prevention:**
```typescript
// BAD - Cell component receives entire row object
interface StageCellProps {
  rowData: Contact;  // If ANY field on contact changes, cell re-renders
  stage: string;
}

const StageCell: React.FC<StageCellProps> = ({ rowData, stage }) => {
  // This re-renders even if only rowData.email changed
  return <div>{rowData.stages[stage]?.completed ? '✓' : ''}</div>;
};

// GOOD - Cell receives only data it needs, wrapped in React.memo
interface StageCellProps {
  contactId: string;
  stageCompleted: boolean;
  stageTimestamp: string | null;
  onToggle: (contactId: string, stage: string) => void;
  stage: string;
}

const StageCell: React.FC<StageCellProps> = React.memo(({
  contactId,
  stageCompleted,
  stageTimestamp,
  onToggle,
  stage
}) => {
  // Only re-renders when stageCompleted or stageTimestamp changes
  return (
    <div onClick={() => onToggle(contactId, stage)}>
      {stageCompleted ? '✓' : ''}
      {stageTimestamp && <span className="text-xs">{formatDate(stageTimestamp)}</span>}
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if stage-specific props changed
  return (
    prevProps.stageCompleted === nextProps.stageCompleted &&
    prevProps.stageTimestamp === nextProps.stageTimestamp
  );
});

// Memoize callback to prevent new function reference on parent re-render
const handleToggleStage = useCallback((contactId: string, stage: string) => {
  updateStageMutation.mutate({ contactId, stage });
}, [updateStageMutation]);

// Memoize data transformation
const gridData = useMemo(() => {
  return contacts.map(contact => ({
    contactId: contact.id,
    name: contact.name,
    stages: stages.reduce((acc, stage) => ({
      ...acc,
      [stage.name]: {
        completed: contact.currentStage === stage.name,
        timestamp: contact.stageEvents.find(e => e.stage === stage.name)?.createdAt
      }
    }), {})
  }));
}, [contacts]);
```

**Detection:**
- React DevTools Profiler showing >500ms render time for grid component
- Chrome Performance tab showing long JavaScript tasks during grid interaction
- Console.log in cell component firing 700 times for single update

**Phase:** Phase 3 (Grid UI) — implement memoization from start, refactoring later is painful

**Sources:**
- [React Data Grid Performance](https://mui.com/x/react-data-grid/performance/)
- [Advanced Performance Patterns for React Data Grids](https://medium.com/@sapnakul/advanced-performance-patterns-for-react-data-grids-real-world-lessons-generic-solutions-4498e3594581)
- [Memoization Guide - Material React Table](https://www.material-react-table.com/docs/guides/memoization)

---

### Pitfall 5: Checkmark Lies (Stale Data Masquerading as Current)

**What goes wrong:** Grid shows checkmark for "Meeting Complete" but event happened 3 months ago. Contact has since ghosted. Checkmark implies freshness/completion when activity is actually stale. Missionary wastes time on cold leads thinking they're active.

**Why it happens:** Binary "completed" state (checkmark vs empty) doesn't encode recency. 3-month-old meeting completion looks identical to yesterday's. Users assume visual confirmation means "current/active" not "ever happened."

**Consequences:**
- Missionaries deprioritize truly active contacts, focus on stale ones
- Reports show "90% meeting completion" but half are 6+ months old
- Loss of trust in the tool: "The journal doesn't show what's actually happening"
- Decision-making based on misleading visual indicators

**Prevention:**
```typescript
// BAD - Binary checkmark with no freshness indicator
const StageCell = ({ completed }: { completed: boolean }) => {
  return <div>{completed ? '✓' : ''}</div>;
};

// GOOD - Encode freshness in visual design
const StageCell = ({
  completed,
  timestamp
}: {
  completed: boolean;
  timestamp: Date | null
}) => {
  if (!completed) return <div className="text-gray-300">—</div>;

  const daysAgo = timestamp
    ? Math.floor((Date.now() - timestamp.getTime()) / (1000 * 60 * 60 * 24))
    : null;

  // Visual freshness encoding
  const freshnessClass = daysAgo === null ? 'text-gray-400' :
    daysAgo < 7 ? 'text-green-600' :      // Recent (< 1 week)
    daysAgo < 30 ? 'text-yellow-600' :    // Aging (1 week - 1 month)
    daysAgo < 90 ? 'text-orange-600' :    // Stale (1-3 months)
    'text-red-400';                        // Very stale (3+ months)

  return (
    <div className="flex items-center gap-1">
      <span className={freshnessClass}>✓</span>
      {daysAgo !== null && (
        <span className="text-xs text-gray-500">
          {daysAgo < 7 ? `${daysAgo}d` :
           daysAgo < 30 ? `${Math.floor(daysAgo / 7)}w` :
           daysAgo < 90 ? `${Math.floor(daysAgo / 30)}mo` :
           `${Math.floor(daysAgo / 30)}mo`}
        </span>
      )}
    </div>
  );
};

// Backend: Include freshness warnings in API response
class JournalContactSerializer(serializers.ModelSerializer):
    stages = serializers.SerializerMethodField()

    def get_stages(self, obj):
        stages_data = {}
        for stage_event in obj.stage_events.all():
            days_since = (timezone.now() - stage_event.created_at).days

            stages_data[stage_event.stage] = {
                'completed': True,
                'timestamp': stage_event.created_at.isoformat(),
                'days_ago': days_since,
                'is_stale': days_since > 90,  # Flag for business logic
                'staleness_level': (
                    'fresh' if days_since < 7 else
                    'aging' if days_since < 30 else
                    'stale' if days_since < 90 else
                    'very_stale'
                )
            }
        return stages_data
```

**Detection:**
- User feedback: "I followed up on contacts marked complete but they were dead ends"
- Analytics showing low conversion despite high stage completion rates
- Variance between "stage complete timestamp" and "last activity timestamp"

**Phase:** Phase 3 (Grid UI) — design visual language for freshness from mockups

**Alternative approach:** Add "Activity Age" column showing days since last stage event, color-coded. Gives missionary quick scan for which contacts are active vs stale.

**Sources:**
- [Stale Data: How to Identify and Mitigate](https://www.acceldata.io/blog/how-to-identify-and-eliminate-stale-data-to-optimize-business-decisions)
- [Data Freshness Best Practices](https://www.elementary-data.com/post/data-freshness-best-practices-and-key-metrics-to-measure-success)
- [PatternFly Stale Data Warning](https://www.patternfly.org/component-groups/status-and-state-indicators/stale-data-warning/)

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 6: Sequential Pipeline Enforcement Too Rigid or Too Loose

**What goes wrong:** Business rule is "sequential-but-flexible" (warn on skip, don't block). Implementation is either too rigid (blocks skip → missionary can't record reality) or too loose (no warning → bad data accumulates silently).

**Why it happens:** Validation logic confuses "warning" with "error." Backend returns 400 status for skip attempt, frontend interprets as blocking error. Or: validation disabled entirely because requirements said "flexible."

**Consequences:**
- Too rigid: Missionary can't log "Contact ghosted before meeting" (stage skip blocked)
- Too loose: Journal fills with nonsensical data (Decision made before Contact stage)
- Support tickets: "System won't let me save" or "How did this contact skip 4 stages?"

**Prevention:**
```python
# BAD - Blocking validation
def create_stage_event(contact, journal, stage):
    current_stage_index = STAGE_ORDER.index(contact.current_stage)
    new_stage_index = STAGE_ORDER.index(stage)

    if new_stage_index > current_stage_index + 1:
        raise ValidationError("Cannot skip stages")  # Blocks save

    StageEvent.objects.create(...)

# GOOD - Non-blocking warning with metadata
STAGE_ORDER = ['CONTACT', 'MEET', 'ASK', 'DECISION', 'THANK', 'NEXT_STEPS']

def create_stage_event(contact, journal, stage):
    current_stage_index = STAGE_ORDER.index(contact.current_stage)
    new_stage_index = STAGE_ORDER.index(stage)

    # Calculate skip severity
    stages_skipped = new_stage_index - current_stage_index - 1
    is_skip = stages_skipped > 0
    is_backward = new_stage_index < current_stage_index

    # Create event with warning metadata (doesn't block save)
    event = StageEvent.objects.create(
        contact=contact,
        journal=journal,
        stage=stage,
        metadata={
            'stages_skipped': stages_skipped,
            'is_skip': is_skip,
            'is_backward': is_backward,
            'skip_severity': 'high' if stages_skipped > 2 else 'low'
        }
    )

    # Optional: Create warning event in audit log
    if is_skip:
        Event.objects.create(
            type='stage_skip_warning',
            message=f"Skipped {stages_skipped} stage(s): {contact.name}",
            severity='warning'
        )

    return event

# Frontend shows warning but allows save
const handleStageUpdate = async (stage: string) => {
  const response = await updateStage({ contactId, journalId, stage });

  if (response.metadata?.is_skip) {
    toast.warning(
      `Warning: Skipped ${response.metadata.stages_skipped} stage(s). ` +
      `Consider logging intermediate stages for accurate tracking.`,
      { duration: 5000 }
    );
  }

  // Save succeeds regardless of warning
};
```

**Detection:**
- Support tickets about "can't save stage"
- Analytics showing 0% stage skip rate (suggests overly rigid validation)
- Analytics showing 40%+ skip rate (suggests too loose, bad data quality)

**Phase:** Phase 2 (Stage Events) — define warning vs error semantics in requirements

**Guideline:** Block only impossible states (e.g., stage doesn't exist). Warn on unusual patterns (skip, backward). Let user override all warnings.

**Sources:**
- [Data Validation in ETL - 2026 Guide](https://www.integrate.io/blog/data-validation-etl/)
- [Validation Pipelines - Explanation & Examples](https://www.secoda.co/glossary/validation-pipelines)

---

### Pitfall 7: Grid Virtualization Not Enabled for >50 Rows

**What goes wrong:** Grid renders all 200 contacts × 7 columns = 1400 DOM nodes on page load. Browser becomes sluggish, scrolling lags, mobile devices crash.

**Why it happens:** React table libraries default to rendering all rows. Developer assumes library handles virtualization automatically. Only 10 rows visible at once, but 190 rows rendered offscreen consuming memory.

**Consequences:**
- Page load time: 4+ seconds for 200-contact grid
- Scrolling framerate drops to 20 FPS (should be 60)
- Mobile Safari crashes with "page unresponsive" error
- Accessibility tools (screen readers) choke on 1400 elements

**Prevention:**
```typescript
// BAD - No virtualization
import { useReactTable, getCoreRowModel } from '@tanstack/react-table';

const JournalGrid = ({ contacts }: { contacts: Contact[] }) => {
  const table = useReactTable({
    data: contacts,  // All 200 rows rendered
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div>
      {table.getRowModel().rows.map(row => (
        <GridRow key={row.id} row={row} />  // 200 DOM nodes
      ))}
    </div>
  );
};

// GOOD - Virtualization with TanStack Virtual
import { useReactTable, getCoreRowModel } from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';

const JournalGrid = ({ contacts }: { contacts: Contact[] }) => {
  const table = useReactTable({
    data: contacts,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: table.getRowModel().rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,  // Row height in pixels
    overscan: 10,  // Render 10 rows above/below viewport for smooth scrolling
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}>
        {rowVirtualizer.getVirtualItems().map(virtualRow => {
          const row = table.getRowModel().rows[virtualRow.index];
          return (
            <GridRow
              key={row.id}
              row={row}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
```

**Detection:**
- Chrome DevTools Performance: "Long task" warnings during scroll
- React DevTools Profiler: 1000+ components rendered
- Lighthouse report: "Avoid enormous network payloads" (if fetching all 200 contacts)

**Phase:** Phase 3 (Grid UI) — enable virtualization before testing with realistic data volume

**Threshold:** Enable virtualization when rows exceed viewport capacity. For 60px row height and 600px viewport: 10 visible rows → virtualize at 50+ total rows.

**Sources:**
- [React Data Grid Performance - KendoReact](https://www.telerik.com/kendo-react-ui/components/grid/performance)
- [Virtual Scrolling/Virtualization](https://js.devexpress.com/React/Documentation/Guide/UI_Components/DataGrid/Enhance_Performance_on_Large_Datasets/)

---

### Pitfall 8: Decision History Queries Without Pagination

**What goes wrong:** Contact has 50 decision updates over 2 years. Opening decision history panel fetches all 50 records, renders 50 table rows, takes 3 seconds to load. Most users only care about recent 5-10.

**Why it happens:** "History" implies "show everything." Developer queries `DecisionHistory.objects.filter(decision=decision).all()` without limit. Works fine with 3 history records during testing. Breaks in production with real usage.

**Consequences:**
- Decision panel slow to open (bad UX)
- Large payload size (50 records × verbose JSON = 100KB response)
- Database query scans full history table instead of using LIMIT

**Prevention:**
```python
# BAD - Fetch all history
class DecisionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    def list(self, request, decision_pk=None):
        history = DecisionHistory.objects.filter(
            decision_id=decision_pk
        ).order_by('-changed_at')  # Could be 100+ records

        serializer = DecisionHistorySerializer(history, many=True)
        return Response(serializer.data)

# GOOD - Paginate with default limit
class DecisionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination  # Default 25 per page

    def list(self, request, decision_pk=None):
        # Recent-first ordering
        history = DecisionHistory.objects.filter(
            decision_id=decision_pk
        ).select_related('decision__contact').order_by('-changed_at')

        # Pagination handled by DRF
        page = self.paginate_queryset(history)
        serializer = DecisionHistorySerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

# Frontend: Infinite scroll for history
const DecisionHistoryPanel = ({ decisionId }: { decisionId: string }) => {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['decisionHistory', decisionId],
    queryFn: ({ pageParam = 1 }) =>
      fetchDecisionHistory(decisionId, { page: pageParam }),
    getNextPageParam: (lastPage) => lastPage.next ? lastPage.page + 1 : undefined,
  });

  return (
    <div>
      {data?.pages.map(page =>
        page.results.map(historyItem => (
          <HistoryRow key={historyItem.id} item={historyItem} />
        ))
      )}

      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          Load More History
        </button>
      )}
    </div>
  );
};
```

**Detection:**
- Network tab showing >100KB JSON responses for history endpoint
- Slow query logs showing `SELECT * FROM decision_history WHERE decision_id = X` without LIMIT
- User complaint: "History takes forever to load"

**Phase:** Phase 2 (Decision Tracking) — design history API with pagination from start

**Guideline:** Default to 25 most recent history records. Provide "Load More" or infinite scroll for older history. 90% of usage views recent 5-10 records only.

---

### Pitfall 9: Event Sourcing Signal Handlers Creating Infinite Loops

**What goes wrong:** StageEvent creation triggers signal → signal updates JournalContact.current_stage → save() triggers Contact post_save signal → creates another StageEvent → infinite loop.

**Why it happens:** Django signals fire on every save(). Event sourcing creates events on state changes. State changes trigger saves. Without proper signal guards, circular dependencies emerge.

**Consequences:**
- RecursionError: maximum recursion depth exceeded
- Database deadlocks from concurrent signal processing
- Event table fills with duplicate events
- Production outage requiring database rollback

**Prevention:**
```python
# BAD - No signal guard
@receiver(post_save, sender=StageEvent)
def update_current_stage(sender, instance, created, **kwargs):
    if created:
        journal_contact = JournalContact.objects.get(
            contact=instance.contact,
            journal=instance.journal
        )
        journal_contact.current_stage = instance.stage
        journal_contact.save()  # Triggers JournalContact post_save signal!

@receiver(post_save, sender=JournalContact)
def log_stage_change(sender, instance, **kwargs):
    StageEvent.objects.create(  # Creates new StageEvent!
        contact=instance.contact,
        journal=instance.journal,
        stage=instance.current_stage
    )
    # INFINITE LOOP

# GOOD - Signal guards with update() and created flag
@receiver(post_save, sender=StageEvent)
def update_current_stage(sender, instance, created, **kwargs):
    if created:  # Only process new events, not updates
        # Use update() instead of save() to skip signals
        JournalContact.objects.filter(
            contact=instance.contact,
            journal=instance.journal
        ).update(
            current_stage=instance.stage,
            last_stage_change=instance.created_at
        )

# Alternative: Explicit signal control
from django.db.models.signals import post_save

def update_decision_with_history(decision, amount, cadence):
    # Manually disconnect signal before save
    post_save.disconnect(create_decision_event, sender=Decision)

    try:
        decision.amount = amount
        decision.save()

        # Manually create event (signal won't fire)
        StageEvent.objects.create(...)
    finally:
        # Reconnect signal
        post_save.connect(create_decision_event, sender=Decision)
```

**Detection:**
- Server logs showing RecursionError stack traces
- Database showing duplicate events with identical timestamps
- Pytest tests hanging indefinitely on signal-triggering operations

**Phase:** Phase 1 (Data Model) — design signal architecture before implementing event sourcing

**Guideline:** Prefer explicit event creation over implicit signals for event sourcing. Signals are useful for audit logging, but create/update separation should be manual in business logic.

**Sources:**
- [Event-Driven Architectures with Django](https://www.scoutapm.com/blog/event-driven-architectures-with-django)

---

### Pitfall 10: Grid State Management Without Optimistic Updates

**What goes wrong:** User clicks to mark stage complete → request sent to backend → user waits 500ms staring at unchanged grid → response returns → grid updates. Feels sluggish and unresponsive.

**Why it happens:** Standard React Query pattern waits for server response before updating UI. Works for forms, but grids require instant feedback for good UX.

**Consequences:**
- User clicks multiple times thinking first click didn't register (double/triple submit)
- Grid feels "laggy" compared to Google Sheets or Airtable
- Poor perceived performance even when actual latency is low

**Prevention:**
```typescript
// BAD - No optimistic update
const StageCell = ({ contactId, stage, completed }: StageCellProps) => {
  const updateMutation = useMutation({
    mutationFn: (data) => updateStageEvent(contactId, stage, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['journalGrid']);  // Refetch after success
    },
  });

  const handleToggle = () => {
    updateMutation.mutate({ completed: !completed });
    // UI doesn't update until onSuccess callback fires (500ms delay)
  };

  return <div onClick={handleToggle}>{completed ? '✓' : ''}</div>;
};

// GOOD - Optimistic update with rollback on error
const StageCell = ({ contactId, journalId, stage, completed }: StageCellProps) => {
  const queryClient = useQueryClient();

  const updateMutation = useMutation({
    mutationFn: (data) => updateStageEvent(contactId, journalId, stage, data),

    // Update UI immediately before request completes
    onMutate: async (newData) => {
      // Cancel ongoing queries to avoid overwriting optimistic update
      await queryClient.cancelQueries(['journalGrid', journalId]);

      // Snapshot current state for rollback
      const previousData = queryClient.getQueryData(['journalGrid', journalId]);

      // Optimistically update cache
      queryClient.setQueryData(['journalGrid', journalId], (old: any) => {
        return old.map((contact: any) =>
          contact.id === contactId
            ? {
                ...contact,
                stages: {
                  ...contact.stages,
                  [stage]: {
                    ...contact.stages[stage],
                    completed: newData.completed,
                    timestamp: new Date().toISOString(),
                  }
                }
              }
            : contact
        );
      });

      return { previousData };  // Return context for rollback
    },

    // Rollback on error
    onError: (err, newData, context) => {
      queryClient.setQueryData(['journalGrid', journalId], context?.previousData);
      toast.error('Failed to update stage. Changes reverted.');
    },

    // Refetch to sync with server truth
    onSettled: () => {
      queryClient.invalidateQueries(['journalGrid', journalId]);
    },
  });

  const handleToggle = () => {
    updateMutation.mutate({ completed: !completed });
    // UI updates instantly, then syncs with server
  };

  return (
    <div
      onClick={handleToggle}
      className={updateMutation.isLoading ? 'opacity-50' : ''}
    >
      {completed ? '✓' : ''}
    </div>
  );
};
```

**Detection:**
- User feedback: "Grid feels slow" despite <500ms backend response times
- Analytics showing high rate of duplicate API calls (user clicking multiple times)

**Phase:** Phase 3 (Grid UI) — implement optimistic updates for all grid mutations

**Guideline:** Any grid cell mutation (stage toggle, decision update) should use optimistic updates. Forms and modals can wait for server response. Grids require instant feedback.

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 11: Hover Tooltips Without Debounce

**What goes wrong:** User moves mouse across grid, hover tooltip fetches event timeline for every cell, creates 20 API requests in 2 seconds, tooltip flickers rapidly.

**Why it happens:** Tooltip shows event details on hover. Developer binds fetch to `onMouseEnter` without debounce. Rapid mouse movement triggers fetch spam.

**Consequences:**
- Tooltip content flashes as requests race
- Network tab shows 50+ concurrent requests
- Backend rate limiter may block user
- Annoying UX (tooltip appears/disappears rapidly)

**Prevention:**
```typescript
// BAD - Immediate fetch on hover
const StageCell = ({ contactId, stage }: StageCellProps) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const { data: events } = useQuery({
    queryKey: ['stageEvents', contactId, stage],
    queryFn: () => fetchStageEvents(contactId, stage),
    enabled: showTooltip,  // Fetches immediately on hover
  });

  return (
    <div
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Tooltip content */}
    </div>
  );
};

// GOOD - Debounced hover with delay
import { useDebouncedValue } from '@/hooks/useDebouncedValue';

const StageCell = ({ contactId, stage }: StageCellProps) => {
  const [isHovered, setIsHovered] = useState(false);
  const debouncedHover = useDebouncedValue(isHovered, 300);  // 300ms delay

  const { data: events } = useQuery({
    queryKey: ['stageEvents', contactId, stage],
    queryFn: () => fetchStageEvents(contactId, stage),
    enabled: debouncedHover,  // Only fetch if hover sustained for 300ms
    staleTime: 60000,  // Cache for 1 minute
  });

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {debouncedHover && events && (
        <Tooltip events={events} />
      )}
    </div>
  );
};

// Debounce utility hook
export const useDebouncedValue = <T,>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};
```

**Detection:**
- Network tab showing burst of 20+ requests when moving mouse across grid
- Backend logs showing spike in tooltip endpoint hits
- User complaint: "Tooltip keeps disappearing"

**Phase:** Phase 3 (Grid UI) — add debounce to hover interactions

**Guideline:** 300ms debounce for hover tooltips. Cache tooltip data for 1 minute to avoid refetch on re-hover.

---

### Pitfall 12: Exporting CSV Without Streaming for Large Journals

**What goes wrong:** User clicks "Export CSV" for 500-contact journal → backend queries all 500 contacts + events + decisions into memory → serializes 5MB CSV → browser download. Takes 20 seconds, times out on slow connections.

**Why it happens:** Export implemented as single endpoint returning full CSV file. Works fine with 50 contacts. Breaks with 500+ due to memory/timeout constraints.

**Consequences:**
- Export timeout (30-second Gunicorn timeout)
- Backend memory spike (500 contacts × 10 events each = 5000 objects in memory)
- Browser hangs waiting for download

**Prevention:**
```python
# BAD - Load all data into memory
from django.http import HttpResponse
import csv

def export_journal_csv(request, journal_id):
    journal = Journal.objects.get(pk=journal_id)

    # Loads all 500 contacts + related data into memory
    contacts = Contact.objects.filter(
        journals=journal
    ).prefetch_related('stage_events', 'decisions')

    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)

    for contact in contacts:  # 500 iterations in memory
        writer.writerow([contact.name, contact.email, ...])

    return response

# GOOD - Streaming response with iterator
from django.http import StreamingHttpResponse

class Echo:
    """An object that implements just the write method of the file-like interface."""
    def write(self, value):
        return value

def export_journal_csv(request, journal_id):
    journal = Journal.objects.get(pk=journal_id)

    # Iterator-based queryset (doesn't load all into memory)
    contacts = Contact.objects.filter(
        journals=journal
    ).prefetch_related('stage_events', 'decisions').iterator(chunk_size=100)

    def csv_rows():
        """Generator yielding CSV rows"""
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)

        # Yield header
        yield writer.writerow(['Name', 'Email', 'Current Stage', ...])

        # Yield rows in chunks
        for contact in contacts:
            yield writer.writerow([
                contact.name,
                contact.email,
                contact.current_stage,
                ...
            ])

    response = StreamingHttpResponse(csv_rows(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="journal_{journal_id}.csv"'
    return response
```

**Detection:**
- Export endpoint taking >10 seconds for large journals
- Backend memory usage spiking during export
- Timeout errors in production logs

**Phase:** Phase 4 (Reports) — implement streaming for CSV export

**Threshold:** Use streaming response when export may exceed 1000 rows or 1MB file size.

---

### Pitfall 13: Missing Indexes on Event Query Patterns

**What goes wrong:** Query for "all stage events for contact X in journal Y" scans full events table (10M rows) instead of using index. Takes 5 seconds instead of 50ms.

**Why it happens:** Developer adds `StageEvent` model with foreign keys but forgets composite index for common query pattern: `filter(contact=X, journal=Y).order_by('-created_at')`.

**Consequences:**
- Slow grid page loads (each contact queries events)
- Database CPU spikes under concurrent users
- Query timeout on large event tables

**Prevention:**
```python
# BAD - No composite index
class StageEvent(TimeStampedModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    stage = models.CharField(max_length=50)
    event_type = models.CharField(max_length=50)

    class Meta:
        ordering = ['-created_at']
    # Missing: index for common query patterns

# GOOD - Composite indexes for query patterns
class StageEvent(TimeStampedModel):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, db_index=True)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, db_index=True)
    stage = models.CharField(max_length=50, db_index=True)
    event_type = models.CharField(max_length=50)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Common query: latest event per contact per journal
            models.Index(fields=['contact', 'journal', '-created_at'],
                        name='stageevent_contact_journal_created'),

            # Stage-specific queries
            models.Index(fields=['journal', 'stage', '-created_at'],
                        name='stageevent_journal_stage_created'),

            # Timeline queries
            models.Index(fields=['journal', '-created_at'],
                        name='stageevent_journal_timeline'),
        ]

# Verify index usage with EXPLAIN ANALYZE
# In Django shell:
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as queries:
    events = StageEvent.objects.filter(
        contact_id=contact_id,
        journal_id=journal_id
    ).order_by('-created_at')[:10]
    list(events)  # Force evaluation

print(queries[0]['sql'])
# Should show "Index Scan using stageevent_contact_journal_created"
```

**Detection:**
- Django Debug Toolbar showing queries >100ms
- PostgreSQL slow query log showing sequential scans
- `EXPLAIN ANALYZE` showing "Seq Scan" instead of "Index Scan"

**Phase:** Phase 1 (Data Model) — add indexes during migration creation

**Guideline:** Add composite index for every common filter+order_by pattern. Profile with `EXPLAIN ANALYZE` before production deploy.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Data Model | N+1 queries from event replay (Pitfall #1) | Design with denormalized current_stage field, not pure event sourcing |
| Phase 1: Data Model | Missing composite indexes (Pitfall #13) | Add indexes for (contact, journal, created_at) patterns during migration |
| Phase 1: Data Model | Signal infinite loops (Pitfall #9) | Use `update()` instead of `save()` in signal handlers, test signal chains |
| Phase 2: Decision Tracking | Atomic transaction scope bugs (Pitfall #2) | Use `@transaction.atomic` for all multi-model writes, write tests for rollback scenarios |
| Phase 2: Decision Tracking | History queries without pagination (Pitfall #8) | Design history API with pagination from start, default 25 records |
| Phase 2: Stage Events | Sequential validation too rigid/loose (Pitfall #6) | Implement warnings not errors, log skip metadata for analytics |
| Phase 3: Grid UI | Cell re-render cascade (Pitfall #4) | Use React.memo and prop minimization from first implementation |
| Phase 3: Grid UI | No virtualization for >50 rows (Pitfall #7) | Enable TanStack Virtual before testing with realistic data |
| Phase 3: Grid UI | Checkmark lies about freshness (Pitfall #5) | Design visual language for freshness (color, recency text) in mockups |
| Phase 3: Grid UI | No optimistic updates (Pitfall #10) | Implement optimistic updates for all grid mutations using React Query |
| Phase 3: Grid UI | Hover tooltip spam (Pitfall #11) | Add 300ms debounce to hover fetches, cache tooltip data |
| Phase 4: Reports | CSV export memory issues (Pitfall #12) | Use streaming response with iterator for exports >1000 rows |

## Sources

**Event Sourcing:**
- [GitHub - pyeventsourcing/eventsourcing-django](https://github.com/pyeventsourcing/eventsourcing-django)
- [Event-Driven Architectures with Django](https://www.scoutapm.com/blog/event-driven-architectures-with-django)
- [Snapshot Strategies: Optimizing Event Replays](https://dev.to/alex_aslam/snapshot-strategies-optimizing-event-replays-36oo)
- [Optimizing Event Replays - EventSourcingDB](https://docs.eventsourcingdb.io/best-practices/optimizing-event-replays/)
- [Event Sourcing in production](https://ep2024.europython.eu/session/event-sourcing-in-production/)

**Django Performance:**
- [Django's transaction.atomic()](https://charemza.name/blog/posts/django/postgres/transactions/not-as-atomic-as-you-may-think/)
- [The trouble with transaction.atomic](https://seddonym.me/2020/11/19/trouble-atomic/)
- [Optimize Django Query Performance](https://johnnymetz.com/posts/combine-select-related-prefetch-related/)
- [Optimizing Django Queries with select_related and prefetch_related](https://medium.com/django-unleashed/optimizing-django-queries-with-select-related-and-prefetch-related-e404af72e0eb)
- [Django select_related and prefetch_related](https://betterprogramming.pub/django-select-related-and-prefetch-related-f23043fd635d)

**React Grid Performance:**
- [React Data Grid Performance - MUI X](https://mui.com/x/react-data-grid/performance/)
- [React Data Grid Performance - KendoReact](https://www.telerik.com/kendo-react-ui/components/grid/performance)
- [Advanced Performance Patterns for React Data Grids](https://medium.com/@sapnakul/advanced-performance-patterns-for-react-data-grids-real-world-lessons-generic-solutions-4498e3594581)
- [Memoization Guide - Material React Table](https://www.material-react-table.com/docs/guides/memoization)
- [Build Tables in React: Data Grid Performance Guide](https://strapi.io/blog/table-in-react-performance-guide)

**Data Freshness & UX:**
- [Stale Data: How to Identify and Mitigate](https://www.acceldata.io/blog/how-to-identify-and-eliminate-stale-data-to-optimize-business-decisions)
- [Data Freshness Best Practices](https://www.elementary-data.com/post/data-freshness-best-practices-and-key-metrics-to-measure-success)
- [PatternFly Stale Data Warning](https://www.patternfly.org/component-groups/status-and-state-indicators/stale-data-warning/)

**Pipeline & Kanban:**
- [Kanban Board Best Practices](https://gmelius.com/blog/kanban-board-strategy-guide)
- [Pipeline Kanban View to Power Sales Performance](https://www.moonstride.com/pipeline-kanban-view/)
- [Data Validation in ETL - 2026 Guide](https://www.integrate.io/blog/data-validation-etl/)
- [Validation Pipelines](https://www.secoda.co/glossary/validation-pipelines)

---

*Research confidence: MEDIUM-HIGH*
*Areas researched: Event sourcing patterns, Django atomic transactions, React grid performance, data freshness UX, sequential pipeline validation*
*Gaps: Specific DonorCRM codebase patterns (mitigated by reading existing ARCHITECTURE.md and STACK.md)*
