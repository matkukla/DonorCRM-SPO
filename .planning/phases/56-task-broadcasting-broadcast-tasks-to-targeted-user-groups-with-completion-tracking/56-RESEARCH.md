# Phase 56: Task Broadcasting - Research

**Researched:** 2026-03-24
**Domain:** Full-stack broadcast task system (Django + React)
**Confidence:** HIGH

## Summary

Task Broadcasting adds a system where admins and supervisors can create a single task definition that gets distributed as individual Task copies to targeted groups of users. Each recipient sees the task in their regular Tasks tab and can mark it complete. The sender tracks completion progress via dedicated tracking views.

The implementation is primarily a model extension (new BroadcastTask parent model + FK on existing Task), new API endpoints for CRUD and tracking, and new frontend components (broadcast creation dialog, tracking pages, visual badges). The existing Task infrastructure (model, serializers, hooks, list views, dashboard needs-attention) handles most of the recipient-side experience automatically since broadcast copies are regular Task instances with an owner FK.

**Primary recommendation:** Add a BroadcastTask model as a lightweight parent record (sender, target spec, title/description/due_date/priority snapshot). Add a nullable `broadcast` FK on the existing Task model. Create a new `apps/tasks/broadcast_views.py` for API endpoints and `apps/tasks/broadcast_serializers.py` for serializers. On the frontend, add a BroadcastTaskDialog component, tracking page/section, and broadcast badge to TaskList.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Separate "Broadcast Task" button next to existing "New Task" button on Tasks page -- visible only to admin and supervisor roles
- Broadcast tasks visually distinguished in task list with Megaphone icon badge + "Assigned by [Name]" subtitle text
- Broadcast creation form uses a dialog (same pattern as TaskForm) -- consistent with existing task creation flow
- Confirmation dialog before sending: "This will create a task for X users. Proceed?"
- Admin broadcast tracking: new "/admin/broadcasts" page linked from Admin sidebar section
- Supervisor broadcast tracking: new section on Team page ("Broadcast Tasks" below existing team content)
- Completion progress displayed as fraction + mini progress bar ("28/40" with colored bar) -- compact, scannable
- Broadcast detail uses DataTable with sort/filter for per-user status -- consistent with all other list views
- Supervisor target options: "My Team" radio (all supervised) + "Specific Members" with multi-select -- mirrors admin's pattern
- Admin can target "All Missionaries", "All Supervisors", or "Specific Users"
- Recipient list locked at send time -- edit only changes task content (title, description, due_date, priority), not recipients
- Completed broadcast task copies remain visible to missionary after broadcast is cancelled (historical record)
- Broadcast edit cascades to incomplete copies only; completed copies are untouched
- Cancel removes incomplete copies, keeps completed ones
- Supervisor can only target their supervised missionaries (enforced server-side)
- Missionary can only mark complete (no edit/delete on broadcast tasks)

### Claude's Discretion
- Exact BroadcastTask model field specs (follow existing Task model conventions)
- Service function organization (new services.py or extend existing)
- Broadcast API serializer structure
- View As integration details (broadcast copies are regular tasks -- should work automatically)
- Event creation for new broadcast tasks (follow existing event patterns if straightforward)

### Deferred Ideas (OUT OF SCOPE)
- Recurring broadcasts (monthly auto-send) -- would need a scheduler
- Broadcast templates (save and reuse common task patterns)
- Email/push notifications when broadcast is sent
- Broadcast analytics over time (completion rate trends)
</user_constraints>

<phase_requirements>
## Phase Requirements

Requirements are derived from GitHub Issue #32 acceptance criteria (no formal IDs in REQUIREMENTS.md yet). Assigned IDs for traceability:

| ID | Description | Research Support |
|----|-------------|------------------|
| BC-01 | Admin can create a broadcast task targeting All Missionaries, All Supervisors, or Specific Users | BroadcastTask model + BroadcastCreateView + target resolution service |
| BC-02 | Supervisor can create a broadcast task targeting My Team or Specific Members | Same API with server-side enforcement via supervised_users M2M |
| BC-03 | Each recipient gets their own Task copy in their regular Tasks tab | Task.broadcast FK + bulk_create in broadcast service |
| BC-04 | Broadcast tasks appear in dashboard needs-attention (overdue/due today) | Automatic -- copies are regular Tasks with owner FK |
| BC-05 | Broadcast tasks visually distinguished with Megaphone icon + "Assigned by [Name]" | Frontend Task type extension + broadcast_sender_name serializer field |
| BC-06 | Missionary can mark broadcast task complete but cannot edit/delete | Frontend guard on broadcast FK + backend permission check |
| BC-07 | Admin can view all broadcasts with completion progress at /admin/broadcasts | BroadcastListView + BroadcastDetailView with annotated counts |
| BC-08 | Supervisor can view their broadcasts with completion progress on Team page | Same API filtered by sender=request.user |
| BC-09 | Broadcast edit cascades title/description/due_date/priority to incomplete copies only | BroadcastUpdateView + service function |
| BC-10 | Broadcast cancel removes incomplete copies, keeps completed ones | BroadcastCancelView + service function |
| BC-11 | Confirmation dialog shows recipient count before sending | Frontend count from target resolution API or local calculation |
</phase_requirements>

## Standard Stack

### Core (Already Installed -- No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 5.1.x | Backend framework | Project standard |
| Django REST Framework | 3.15.x | API layer | Project standard |
| django-filter | 24.3 | Query filtering | Project standard (NOT 25.2) |
| React | 19.2 | Frontend framework | Project standard |
| @tanstack/react-query | 5.90.x | Data fetching + cache | Project standard |
| @tanstack/react-table | 8.21.x | DataTable component | Project standard |
| lucide-react | 0.562.x | Icons (Megaphone available) | Project standard |
| @radix-ui/react-dialog | 1.1.x | Dialog component | Project standard |
| @radix-ui/react-progress | 1.1.x | Progress bar | Project standard |
| @radix-ui/react-checkbox | 1.3.x | Checkbox for multi-select | Project standard |
| sonner | 2.0.x | Toast notifications | Project standard |

### No New Packages Required

This phase uses exclusively existing dependencies. No `npm install` or `pip install` needed.

## Architecture Patterns

### Recommended Backend Structure
```
apps/tasks/
  models.py              # Add BroadcastTask model + Task.broadcast FK
  broadcast_views.py     # NEW: Broadcast CRUD + tracking views
  broadcast_serializers.py  # NEW: BroadcastTask serializers
  broadcast_services.py  # NEW: Target resolution + copy creation + cascade logic
  broadcast_filters.py   # NEW: FilterSet for broadcast list
  urls.py                # Add broadcast URL patterns
  migrations/
    0004_broadcasttask.py  # Schema migration
```

### Recommended Frontend Structure
```
frontend/src/
  api/
    broadcasts.ts           # NEW: API client functions + types
  hooks/
    useBroadcasts.ts        # NEW: React Query hooks
  pages/
    tasks/
      TaskList.tsx           # MODIFY: Add "Broadcast Task" button + broadcast badge
      TaskDetail.tsx         # MODIFY: Add broadcast info + restrict actions
      BroadcastTaskDialog.tsx  # NEW: Dialog for creating/editing broadcasts
    admin/
      BroadcastList.tsx      # NEW: /admin/broadcasts page
      BroadcastDetail.tsx    # NEW: /admin/broadcasts/:id detail page
    team/
      TeamPage.tsx           # MODIFY: Add broadcast tracking section
```

### Pattern 1: BroadcastTask Model (Parent Record)
**What:** A new model that stores the broadcast definition. Individual Task copies reference it via FK.
**When to use:** When a single logical action creates multiple child records.
**Example:**
```python
class BroadcastTask(TimeStampedModel):
    """Parent record for a broadcast task distribution."""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_broadcasts',
        db_index=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.OTHER,
    )
    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
    )
    due_date = models.DateField()

    # Target specification (snapshot at send time)
    target_type = models.CharField(
        max_length=30,
        choices=[
            ('all_missionaries', 'All Missionaries'),
            ('all_supervisors', 'All Supervisors'),
            ('specific_users', 'Specific Users'),
            ('my_team', 'My Team'),
        ],
    )
    # Store resolved recipient IDs at send time for audit trail
    recipient_ids = models.JSONField(default=list)
    recipient_count = models.PositiveIntegerField(default=0)

    # Status
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'broadcast_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', '-created_at']),
        ]
```

Then add to existing Task model:
```python
# In Task model
broadcast = models.ForeignKey(
    'tasks.BroadcastTask',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='copies',
    db_index=True,
)
```

### Pattern 2: Broadcast Service (Atomic Operations)
**What:** Service functions that handle target resolution, bulk copy creation, cascade edits, and cancellation -- all in database transactions.
**When to use:** Complex multi-model operations that must be atomic.
**Example:**
```python
# apps/tasks/broadcast_services.py
from django.db import transaction

@transaction.atomic
def create_broadcast(sender, title, description, task_type, priority,
                     due_date, target_type, specific_user_ids=None):
    """Create broadcast + distribute task copies to all recipients."""
    recipients = resolve_recipients(sender, target_type, specific_user_ids)

    broadcast = BroadcastTask.objects.create(
        sender=sender,
        title=title,
        description=description,
        task_type=task_type,
        priority=priority,
        due_date=due_date,
        target_type=target_type,
        recipient_ids=[str(u.id) for u in recipients],
        recipient_count=len(recipients),
    )

    tasks = [
        Task(
            owner=recipient,
            broadcast=broadcast,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            due_date=due_date,
        )
        for recipient in recipients
    ]
    Task.objects.bulk_create(tasks)
    return broadcast


def resolve_recipients(sender, target_type, specific_user_ids=None):
    """Resolve target specification to a concrete list of users."""
    from apps.users.models import User

    if target_type == 'all_missionaries':
        assert sender.role == 'admin'
        return list(User.objects.filter(role='missionary', is_active=True))
    elif target_type == 'all_supervisors':
        assert sender.role == 'admin'
        return list(User.objects.filter(role='supervisor', is_active=True))
    elif target_type == 'my_team':
        assert sender.role in ('admin', 'supervisor')
        return list(sender.supervised_users.filter(is_active=True))
    elif target_type == 'specific_users':
        users = User.objects.filter(id__in=specific_user_ids, is_active=True)
        # Server-side enforcement: supervisor can only target supervised users
        if sender.role == 'supervisor':
            allowed_ids = set(
                sender.supervised_users.filter(is_active=True)
                .values_list('id', flat=True)
            )
            users = users.filter(id__in=allowed_ids)
        return list(users)
    return []
```

### Pattern 3: Annotated Tracking Queries
**What:** Use Django annotations to compute completion stats without N+1 queries.
**When to use:** Any list view showing aggregate counts.
**Example:**
```python
# In broadcast list view queryset
from django.db.models import Count, Q

BroadcastTask.objects.filter(sender=user).annotate(
    completed_count=Count(
        'copies',
        filter=Q(copies__status=TaskStatus.COMPLETED),
    ),
    total_count=Count('copies'),
).order_by('-created_at')
```

### Pattern 4: Frontend Broadcast Badge on TaskList
**What:** Extend the Task type with optional broadcast fields; render Megaphone icon + "Assigned by" text in the title cell.
**When to use:** Distinguishing broadcast copies in the regular task list.
**Example:**
```typescript
// Extended Task type
interface Task {
  // ... existing fields ...
  broadcast_id: string | null
  broadcast_sender_name: string | null
}

// In TaskList title column cell
{row.original.broadcast_id && (
  <div className="flex items-center gap-1.5">
    <Megaphone className="h-3.5 w-3.5 text-muted-foreground" />
    <span className="text-xs text-muted-foreground">
      Assigned by {row.original.broadcast_sender_name}
    </span>
  </div>
)}
```

### Anti-Patterns to Avoid
- **Separate broadcast task table for recipients:** Do NOT create a separate model for broadcast copies. Use the existing Task model with a nullable broadcast FK. This ensures all task features (filters, dashboard, overdue, complete) work automatically.
- **Computing recipient count on the fly:** Lock `recipient_count` and `recipient_ids` at send time. Do not recompute from User queries -- team membership may change after broadcast.
- **Cascade edit via Python loop:** Use `Task.objects.filter(broadcast=broadcast, status__in=[...]).update(...)` for cascade edits, not fetching + saving each task individually.
- **Allowing missionaries to edit broadcast tasks:** Missionaries can only mark complete. Edit/delete are restricted to the broadcast sender (or admin).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk task creation | Custom loop with individual saves | `Task.objects.bulk_create(tasks)` | 1 SQL INSERT vs N |
| Completion tracking aggregation | Python counter over task list | `annotate(Count(..., filter=Q(...)))` | Database-level, no N+1 |
| Progress bar component | Custom div with inline styles | Radix `<Progress>` component (already installed) | Accessible, animated |
| Multi-select user picker | Custom checkbox list | Radix Checkbox + Command (cmdk) combo | Searchable, keyboard accessible, project pattern |
| Confirmation dialog | `window.confirm()` | Radix AlertDialog or Dialog with confirm/cancel buttons | Consistent UX, async-safe |
| URL state management | Manual searchParams | nuqs (already integrated) | Project pattern for filter state |

**Key insight:** The main complexity savings come from reusing the existing Task model for broadcast copies. This gives us dashboard integration, filter support, completion tracking, View As compatibility, and the entire task list UI for free.

## Common Pitfalls

### Pitfall 1: View As Mode Interaction
**What goes wrong:** Broadcast creation form is visible while in View As mode, leading to confusing UX or permission errors.
**Why it happens:** The "Broadcast Task" button visibility check might not account for `isViewingAs`.
**How to avoid:** Hide the "Broadcast Task" button when `isViewingAs` is true, same as the existing "Create Task" button guard. Backend: ViewAsMiddleware already blocks mutations (returns 403 for non-GET when X-View-As-User-Id is set), so this is defense-in-depth.
**Warning signs:** "Mutations are not allowed" 403 error when trying to create broadcast in View As mode.

### Pitfall 2: Supervisor Targeting Bypass
**What goes wrong:** Supervisor submits specific_user_ids containing users outside their supervised_users M2M.
**Why it happens:** Client-side multi-select could be manipulated.
**How to avoid:** Server-side enforcement in `resolve_recipients()`: filter specific_user_ids against `sender.supervised_users` when sender.role == 'supervisor'. Return 400 if no valid recipients remain.
**Warning signs:** Supervisor sees tasks assigned to missionaries they don't supervise.

### Pitfall 3: Race Condition on Cascade Edit
**What goes wrong:** A missionary marks a task complete between the broadcast edit and the cascade update, so the completed task gets its content overwritten.
**Why it happens:** Non-atomic read-then-update pattern.
**How to avoid:** Use a single `Task.objects.filter(broadcast=broadcast).exclude(status=TaskStatus.COMPLETED).update(...)` query. The database handles the atomicity.
**Warning signs:** Completed tasks having their title/description changed after broadcast edit.

### Pitfall 4: UTC Date Display Bug
**What goes wrong:** Due dates on broadcast tasks display as wrong day.
**Why it happens:** `new Date("2026-04-01")` parses as UTC midnight, showing March 31 in US timezones.
**How to avoid:** Use `formatLocalDate()` from `frontend/src/lib/utils.ts` for all date-only strings. This is already used throughout the codebase (TaskList, TaskDetail).
**Warning signs:** Due date showing one day earlier than expected.

### Pitfall 5: Stale React Query Cache After Broadcast
**What goes wrong:** After creating a broadcast, the task list doesn't show the new broadcast copies.
**Why it happens:** Task list uses `["tasks", filters]` query key with 5-minute staleTime.
**How to avoid:** Invalidate `["tasks"]` query key in the broadcast creation mutation's `onSuccess`. Also invalidate `["dashboard"]` since copies appear in needs-attention.
**Warning signs:** New broadcast tasks not visible until page refresh.

### Pitfall 6: Bulk Create Missing UUID PKs
**What goes wrong:** `bulk_create` on models with `UUIDField(default=uuid4)` works correctly in Django 5.1 -- the default is called per-instance. However, signals are NOT fired by `bulk_create`.
**Why it happens:** Django's `bulk_create` skips `post_save` signals for performance.
**How to avoid:** If broadcast task creation needs to fire events, create them explicitly after `bulk_create` (use a separate Event.objects.bulk_create for notifications). For Phase 56, event creation is in Claude's discretion -- keep it simple.
**Warning signs:** Missing Event records for broadcast task creation.

## Code Examples

### Backend: Broadcast URL Patterns
```python
# apps/tasks/urls.py -- additions
from apps.tasks.broadcast_views import (
    BroadcastListCreateView,
    BroadcastDetailView,
    BroadcastCancelView,
    BroadcastCopyListView,
)

urlpatterns += [
    # Broadcast endpoints -- BEFORE <uuid:pk>/ to avoid UUID capture
    path('broadcasts/', BroadcastListCreateView.as_view(), name='broadcast-list'),
    path('broadcasts/<uuid:pk>/', BroadcastDetailView.as_view(), name='broadcast-detail'),
    path('broadcasts/<uuid:pk>/cancel/', BroadcastCancelView.as_view(), name='broadcast-cancel'),
    path('broadcasts/<uuid:pk>/copies/', BroadcastCopyListView.as_view(), name='broadcast-copies'),
]
```

### Backend: Serializer with Annotations
```python
class BroadcastTaskListSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = BroadcastTask
        fields = [
            'id', 'sender', 'sender_name',
            'title', 'description', 'task_type', 'priority', 'due_date',
            'target_type', 'recipient_count',
            'completed_count', 'total_count',
            'is_cancelled', 'created_at',
        ]
```

### Backend: TaskSerializer Extension for Broadcast Info
```python
# Add to existing TaskSerializer
broadcast_id = serializers.UUIDField(source='broadcast.id', read_only=True, allow_null=True)
broadcast_sender_name = serializers.CharField(
    source='broadcast.sender.full_name', read_only=True, allow_null=True
)
```

Note: `select_related('broadcast__sender')` must be added to TaskListCreateView.get_queryset() to avoid N+1 queries.

### Frontend: Broadcast Creation Dialog
```typescript
// Pattern from existing Dialog components (AdminUsers, LogEventDialog)
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent className="sm:max-w-lg">
    <DialogHeader>
      <DialogTitle>Broadcast Task</DialogTitle>
      <DialogDescription>
        Create a task for multiple users at once.
      </DialogDescription>
    </DialogHeader>
    {/* Form fields: title, description, type, priority, due_date */}
    {/* Target selection: radio buttons + multi-select */}
    <DialogFooter>
      <Button variant="secondary" onClick={() => setIsOpen(false)}>Cancel</Button>
      <Button onClick={handleConfirm}>Send to {recipientCount} users</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Frontend: Progress Bar in Tracking View
```typescript
// Compact progress display for broadcast list
function BroadcastProgress({ completed, total }: { completed: number; total: number }) {
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium tabular-nums">
        {completed}/{total}
      </span>
      <Progress value={pct} className="h-2 w-24" />
    </div>
  )
}
```

### Frontend: Broadcast Badge in Task List
```typescript
// In TaskList title column cell renderer
<div>
  <div className="font-medium">{row.original.title}</div>
  {row.original.broadcast_id ? (
    <div className="flex items-center gap-1 mt-0.5">
      <Megaphone className="h-3 w-3 text-muted-foreground" />
      <span className="text-xs text-muted-foreground">
        Assigned by {row.original.broadcast_sender_name}
      </span>
    </div>
  ) : row.original.contact_name ? (
    <Link to={`/contacts/${row.original.contact}`} ...>
      {row.original.contact_name}
    </Link>
  ) : null}
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual Smartsheet tracking of MPD tasks | Broadcast system integrated in DonorCRM | Phase 56 | Replaces external tool with native feature |
| Separate broadcast task model for copies | Nullable FK on existing Task model | Architecture decision | Copies inherit all task behavior automatically |

## Open Questions

1. **Event creation for broadcast tasks**
   - What we know: EventType has TASK_DUE, TASK_OVERDUE, TASK_COMPLETED choices. The events system uses `create_event()` helper.
   - What's unclear: Should we create events for each recipient when broadcast is sent? Could be noisy for large broadcasts.
   - Recommendation: Skip event creation for now. The tasks themselves appear in needs-attention automatically. Defer notification events to the deferred "Email/push notifications" idea.

2. **Broadcast task completion by admin/supervisor sender**
   - What we know: Sender can edit broadcast content and cancel. Missionaries can mark complete.
   - What's unclear: Can the sender also mark a specific copy as complete on behalf of a missionary?
   - Recommendation: No -- keep it simple. Sender can view status but only the task owner (missionary) can mark complete. This matches the existing task permission model.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-django |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest apps/tasks/tests/ -x -q` |
| Full suite command | `pytest apps/tasks/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BC-01 | Admin creates broadcast targeting groups | unit/integration | `pytest apps/tasks/tests/test_broadcast_views.py::TestBroadcastCreate -x` | Wave 0 |
| BC-02 | Supervisor creates broadcast for team only | unit/integration | `pytest apps/tasks/tests/test_broadcast_views.py::TestSupervisorBroadcast -x` | Wave 0 |
| BC-03 | Recipients get Task copies with broadcast FK | unit | `pytest apps/tasks/tests/test_broadcast_services.py::TestCreateBroadcast -x` | Wave 0 |
| BC-04 | Broadcast copies in needs-attention | integration | `pytest apps/dashboard/tests/test_services.py -x -k needs_attention` | Existing (auto) |
| BC-05 | TaskSerializer includes broadcast fields | unit | `pytest apps/tasks/tests/test_broadcast_serializers.py -x` | Wave 0 |
| BC-06 | Missionary cannot edit/delete broadcast tasks | integration | `pytest apps/tasks/tests/test_broadcast_views.py::TestMissionaryRestrictions -x` | Wave 0 |
| BC-07 | Admin sees all broadcasts with counts | integration | `pytest apps/tasks/tests/test_broadcast_views.py::TestBroadcastList -x` | Wave 0 |
| BC-09 | Edit cascades to incomplete copies only | unit | `pytest apps/tasks/tests/test_broadcast_services.py::TestCascadeEdit -x` | Wave 0 |
| BC-10 | Cancel removes incomplete, keeps completed | unit | `pytest apps/tasks/tests/test_broadcast_services.py::TestCancelBroadcast -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/tasks/tests/ -x -q`
- **Per wave merge:** `pytest apps/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/tasks/tests/test_broadcast_services.py` -- covers BC-03, BC-09, BC-10
- [ ] `apps/tasks/tests/test_broadcast_views.py` -- covers BC-01, BC-02, BC-06, BC-07
- [ ] `apps/tasks/tests/test_broadcast_serializers.py` -- covers BC-05
- [ ] `apps/tasks/tests/factories.py` -- add BroadcastTaskFactory

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified). This phase is purely code/config changes using the existing Django + React stack. All required packages (DRF, django-filter, React Query, Radix UI, lucide-react) are already installed.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: apps/tasks/models.py, views.py, serializers.py, filters.py, urls.py
- Codebase inspection: apps/core/permissions.py (get_visible_user_ids, IsOwnerOrAdmin, IsSupervisorWriteRestricted)
- Codebase inspection: apps/users/models.py (User model, supervisors M2M, supervised_users reverse)
- Codebase inspection: apps/events/services.py (create_event pattern)
- Codebase inspection: apps/dashboard/services.py (get_needs_attention -- automatic for broadcast copies)
- Codebase inspection: frontend/src/pages/tasks/TaskList.tsx, TaskForm.tsx, TaskDetail.tsx
- Codebase inspection: frontend/src/pages/team/TeamPage.tsx
- Codebase inspection: frontend/src/pages/admin/AdminUsers.tsx (Dialog pattern reference)
- Codebase inspection: frontend/src/components/ui/ (dialog, progress, checkbox, select components)
- Codebase inspection: frontend/node_modules/lucide-react -- Megaphone icon confirmed available

### Secondary (MEDIUM confidence)
- Django docs: bulk_create behavior with UUIDField defaults and signal skipping
- Django docs: annotate with Count + filter for aggregate queries

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already installed, no new packages needed
- Architecture: HIGH - Follows established project patterns (FK relationships, TimeStampedModel, service layer, Dialog components)
- Pitfalls: HIGH - Identified from direct codebase inspection and known project patterns (UTC bug, stale cache, View As)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependencies, all patterns from existing codebase)
