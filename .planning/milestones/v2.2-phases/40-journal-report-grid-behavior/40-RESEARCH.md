# Phase 40: Journal Report & Grid Behavior - Research

**Researched:** 2026-02-27
**Domain:** Journal report rebuild (metrics, charts, alerts) + grid stage checkbox behavior changes
**Confidence:** HIGH

## Summary

Phase 40 has two distinct workstreams: (1) rebuilding the journal report tab with new activity-focused metrics, charts, and conditional alerts, and (2) changing the grid's stage checkbox behavior from "open drawer on click" to "instant toggle (auto-create stage event)." Both workstreams are well-contained within existing infrastructure.

The report tab currently renders four components (`DecisionTrendsChart`, `PipelineBreakdownChart`, `StageActivityChart`, `NextStepsQueue`) powered by a `JournalAnalyticsViewSet` that returns user-wide data. The new report requires journal-scoped, date-filterable data with different metrics (Total Contacts, With Decisions, Confirmed $, Pending, goal progress, Contacts by Stage bar chart, Decision Status donut chart, stalled contacts alert, open next steps alert). This means a new backend endpoint (or refactored analytics viewset) that accepts `journal_id` and date range params, plus a complete frontend rebuild of the report tab.

The grid behavior change is straightforward: the `StageCell` click handler currently calls `onStageCellClick` which opens the `EventTimelineDrawer`. The new behavior should call `createStageEvent` directly (via the existing `useCreateStageEvent` hook) with a default event type, skip the drawer, and optimistically update the checkbox UI. The Decision column (currently rendered after all stage columns) needs to be repositioned between Close and Thank stage columns per JRNL-07.

**Primary recommendation:** Build a new `journal-report` backend endpoint that aggregates journal-scoped data in a single API call, rebuild the report tab frontend from scratch using existing Recharts/shadcn chart infrastructure, and modify `StageCell` to directly create events on click.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Primary purpose is **activity summary** -- what the missionary has been doing
- Key metrics: stage movements, decisions & gifts, activity volume (journal entries created, tasks completed, notes added)
- **No** contact-level detail -- aggregates only (totals and counts)
- Contact counts by stage are excluded from headline metrics
- **Full rebuild** of the current report -- tear down and rebuild from scratch
- Stays in the existing Reports section on the individual journal page
- Screen-only -- no print or PDF export needed
- Single journal scope -- report always shows data for the journal being viewed
- Admin navigates to a user's journal page to see their report (existing journal page access pattern)
- Currently checkboxes are read-only; changing stages requires opening the contact detail panel
- New behavior: **instant toggle** -- click saves immediately, no confirmation dialog, no undo toast
- Each stage column has its own checkbox -- clicking it marks that stage as reached for the contact
- **Independent toggles** -- stages can be checked in any order, checking stage 4 does NOT auto-check stages 1-3
- Custom date range picker with presets (Last 7 days, Last 30 days, This month, etc.)
- Regular users see their own journal report; admins can see any user's journal report
- Admin accesses other users' reports from the journal page itself (not a separate admin view)

### Claude's Discretion
- Whether to include charts/visualizations or keep it tables-only -- pick what adds clarity for the data
- Whether to include stage filtering (e.g., show only specific stage movements) -- decide based on what makes sense for the chosen metrics
- Visual design, spacing, and component choices for the rebuilt report
- Loading states and empty states for the report

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| JRNL-01 | Journal report displays 4 metric cards (Total Contacts, With Decisions, Confirmed $, Pending) | New `journal-report` backend endpoint returns aggregated counts; frontend renders Card components with these values |
| JRNL-02 | Journal report displays goal progress bar with confirmed amount | Existing `JournalHeader` already has goal progress logic; new report endpoint returns `confirmed_amount` and `goal_amount`; use existing `Progress` shadcn component |
| JRNL-03 | Journal report displays Contacts by Stage bar chart with stage colors | New endpoint returns stage distribution data; Recharts `BarChart` with `STAGE_COLORS` constants already established in `ReportCharts.tsx` |
| JRNL-04 | Journal report displays Decision Status donut chart | New endpoint returns decision status counts; Recharts `PieChart` with status color mapping from `DECISION_STATUS_COLORS` |
| JRNL-05 | Journal report displays conditional stalled contacts and open next steps alerts | Backend computes stalled contacts (no events in N days) and open next steps count; frontend conditionally renders alert sections |
| JRNL-06 | Pipeline Breakdown is removed from journal reports | Remove `PipelineBreakdownChart` from report tab render; existing component stays in codebase (may be used elsewhere) |
| JRNL-07 | Decision column between Close and Thank supports adding a decision (not checkbox) | Reorder grid columns: move `DecisionCell` between Close and Thank stage columns; existing `DecisionCell`/`DecisionDialog` components handle the creation flow |
| JRNL-08 | Clicking a stage checkbox directly checks it (auto-creates event) without dialog | Modify `StageCell` click handler to call `useCreateStageEvent` directly with default event type; bypass `EventTimelineDrawer`; optimistic UI update |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Recharts | ^3.6.0 | Bar chart, donut/pie chart, progress visualization | Already in project, used across dashboard and existing report charts |
| shadcn/ui | (latest) | Card, Progress, Badge, Alert components | Project standard UI library, all needed components already exist |
| @tanstack/react-query | ^5.90.17 | Data fetching, caching, optimistic updates | Project standard for all API communication |
| date-fns | ^4.1.0 | Date formatting, presets, range calculations | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | ^2.0.7 | Toast notifications for stage event creation | Already used for mutation feedback |
| lucide-react | ^0.562.0 | Icons for metric cards and alerts | Already used throughout project |

### Alternatives Considered
None -- all needed libraries already in project.

## Architecture Patterns

### Existing File Structure (will be modified)
```
frontend/src/pages/journals/
├── JournalDetail.tsx           # Main page with Tabs (grid/report)
├── JournalList.tsx             # Journal listing page
└── components/
    ├── JournalGrid.tsx         # Grid with stage columns + decision + next steps
    ├── StageCell.tsx            # Stage checkbox cell (MODIFY: instant toggle)
    ├── DecisionCell.tsx         # Decision card/button (MOVE: reposition in grid)
    ├── DecisionDialog.tsx       # Decision create/edit dialog
    ├── ReportCharts.tsx         # REPLACE: current report charts
    ├── JournalHeader.tsx        # Header with goal progress
    ├── EventTimelineDrawer.tsx  # Timeline drawer (keep, but decouple from stage click)
    ├── LogEventDialog.tsx       # Log event dialog
    ├── NextStepsCell.tsx        # Next steps checklist popover
    └── index.ts                 # Barrel exports

apps/journals/
├── models.py                   # Journal, JournalContact, JournalStageEvent, Decision, NextStep
├── views.py                    # MODIFY: JournalAnalyticsViewSet (add journal-scoped report endpoint)
├── serializers.py              # Add report serializer
├── urls.py                     # Add route for new endpoint
└── filters.py                  # Journal filters
```

### Pattern 1: New Journal Report API Endpoint
**What:** A single backend endpoint that returns all report data for a specific journal, scoped by date range.
**When to use:** When the report tab is loaded.
**Why single endpoint:** Reduces N API calls to 1, simplifies loading state management, allows backend to optimize queries.

```python
# apps/journals/views.py - new action on JournalAnalyticsViewSet
@action(detail=False, methods=['get'], url_path='journal-report')
def journal_report(self, request):
    """
    Aggregated report data for a single journal.
    Params: journal_id (required), date_from, date_to (optional)
    """
    journal_id = request.query_params.get('journal_id')
    if not journal_id:
        return Response({'detail': 'journal_id is required'}, status=400)

    # Verify ownership
    journal = get_object_or_404(Journal, pk=journal_id)
    if not self._is_admin(request) and journal.owner != request.user:
        return Response(status=403)

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    # Base querysets scoped to journal
    members = JournalContact.objects.filter(journal=journal)
    decisions = Decision.objects.filter(journal_contact__journal=journal)
    events = JournalStageEvent.objects.filter(journal_contact__journal=journal)
    next_steps = NextStep.objects.filter(journal_contact__journal=journal)

    # Apply date filters if provided
    if date_from:
        events = events.filter(created_at__date__gte=date_from)
        decisions = decisions.filter(created_at__date__gte=date_from)
    if date_to:
        events = events.filter(created_at__date__lte=date_to)
        decisions = decisions.filter(created_at__date__lte=date_to)

    # Metric cards
    total_contacts = members.count()
    with_decisions = decisions.exclude(status='declined').values('journal_contact').distinct().count()
    confirmed_amount = decisions.filter(status='active').aggregate(total=Sum('amount'))['total'] or 0
    pending_amount = decisions.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    # Contacts by stage (for bar chart)
    stage_distribution = members.annotate(
        current_stage=Subquery(
            JournalStageEvent.objects.filter(
                journal_contact=OuterRef('pk')
            ).order_by('-created_at').values('stage')[:1]
        )
    ).values('current_stage').annotate(count=Count('id'))

    # Decision status distribution (for donut chart)
    decision_status = decisions.values('status').annotate(count=Count('id'))

    # Stalled contacts (no events in 30+ days)
    from datetime import timedelta
    stall_threshold = timezone.now() - timedelta(days=30)
    stalled_count = members.exclude(
        stage_events__created_at__gte=stall_threshold
    ).count()

    # Open next steps count
    open_next_steps = next_steps.filter(completed=False).count()

    return Response({
        'metrics': {
            'total_contacts': total_contacts,
            'with_decisions': with_decisions,
            'confirmed_amount': str(confirmed_amount),
            'pending_amount': str(pending_amount),
        },
        'goal_amount': str(journal.goal_amount),
        'stage_distribution': list(stage_distribution),
        'decision_status': list(decision_status),
        'alerts': {
            'stalled_contacts': stalled_count,
            'open_next_steps': open_next_steps,
        }
    })
```

### Pattern 2: Instant Stage Toggle (JRNL-08)
**What:** Click stage checkbox -> immediately POST stage event -> optimistic UI update.
**When to use:** Every stage cell click in the journal grid.

```typescript
// Modified StageCell behavior
const handleClick = React.useCallback(() => {
  if (!eventSummary.has_events) {
    // Auto-create a stage event with default type
    const defaultEventType = getDefaultEventType(stage)
    createStageEvent({
      journal_contact: journalContactId,
      stage,
      event_type: defaultEventType,
    })
  } else {
    // Already has events - open timeline drawer for details
    onCellClick(contactId, stage)
  }
}, [contactId, stage, eventSummary, journalContactId])

function getDefaultEventType(stage: PipelineStage): StageEventType {
  const defaults: Record<PipelineStage, StageEventType> = {
    contact: 'call_logged',
    meet: 'meeting_completed',
    close: 'ask_made',
    decision: 'decision_received',
    thank: 'thank_you_sent',
    next_steps: 'next_step_created',
  }
  return defaults[stage]
}
```

### Pattern 3: Grid Column Reordering (JRNL-07)
**What:** Move Decision column between Close and Thank stages.
**When to use:** Grid layout in `JournalGrid.tsx`.

Current column order: Contact | Contact(stage) | Meet | Close | Decision(stage) | Thank | Next Steps(stage) | Decision(card) | Next Steps(checklist)

New column order: Contact | Contact(stage) | Meet | Close | Decision(card) | Thank | Next Steps(stage) | Next Steps(checklist)

Key change: The `decision` stage column checkbox is replaced by the `DecisionCell` component (which opens a dialog, not a checkbox). The `PIPELINE_STAGES` array used for rendering stage columns should be filtered to exclude `decision` when rendering stage checkboxes, and the `DecisionCell` should be inserted between Close and Thank in the JSX.

```typescript
// In JournalGrid.tsx
const GRID_STAGE_COLUMNS: PipelineStage[] = ['contact', 'meet', 'close', 'thank', 'next_steps']

// Render: Contact name | contact | meet | close | DecisionCell | thank | next_steps | NextStepsCell
```

### Pattern 4: Report Component Structure (Full Rebuild)
**What:** New report component tree replacing existing charts.
**When to use:** Reports tab content in `JournalDetail.tsx`.

```typescript
// New component: JournalReport.tsx
function JournalReport({ journalId }: { journalId: string }) {
  const [dateRange, setDateRange] = useState<DateRange | null>(null)
  const dateParams = dateRangeToParams(dateRange)

  const { data, isLoading } = useJournalReport(journalId, dateParams)

  return (
    <div className="space-y-6">
      {/* Date range picker */}
      <div className="flex justify-end">
        <DateRangePicker value={dateRange} onChange={setDateRange} />
      </div>

      {/* 4 Metric cards in a row */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard title="Total Contacts" value={data.metrics.total_contacts} />
        <MetricCard title="With Decisions" value={data.metrics.with_decisions} />
        <MetricCard title="Confirmed $" value={formatCurrency(data.metrics.confirmed_amount)} />
        <MetricCard title="Pending" value={formatCurrency(data.metrics.pending_amount)} />
      </div>

      {/* Goal progress bar */}
      <GoalProgressBar confirmed={data.metrics.confirmed_amount} goal={data.goal_amount} />

      {/* Charts row */}
      <div className="grid gap-6 md:grid-cols-2">
        <ContactsByStageChart data={data.stage_distribution} />
        <DecisionStatusChart data={data.decision_status} />
      </div>

      {/* Conditional alerts */}
      {data.alerts.stalled_contacts > 0 && (
        <StalledContactsAlert count={data.alerts.stalled_contacts} />
      )}
      {data.alerts.open_next_steps > 0 && (
        <OpenNextStepsAlert count={data.alerts.open_next_steps} />
      )}
    </div>
  )
}
```

### Anti-Patterns to Avoid
- **Multiple API calls for report data:** Don't make 6 separate API calls for metrics, charts, alerts. Use a single aggregated endpoint.
- **Keeping PipelineBreakdown chart:** JRNL-06 explicitly requires removal. Don't just hide it; remove it from the report render.
- **Re-using existing analytics hooks for the report:** The existing hooks (`useDecisionTrends`, etc.) are user-wide, not journal-scoped. Create a new `useJournalReport` hook.
- **Showing confirmation dialog on stage check:** JRNL-08 says "without dialog." The click must directly create the event.
- **Auto-checking previous stages:** User decision says "Independent toggles -- stages can be checked in any order."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date range picker with presets | Custom date selector | Existing `DateRangePicker` from `components/ui/date-range-picker.tsx` | Already built with presets, calendar, and `dateRangeToParams` helper |
| Bar chart / donut chart | Canvas/SVG from scratch | Recharts via `ChartContainer` from `components/ui/chart.tsx` | Already integrated with shadcn theming and dark mode |
| Progress bar | Custom div-based progress | shadcn `Progress` component (already used in `JournalHeader`) | Accessible, styled, theme-aware |
| Toast notifications | Custom notification system | `sonner` via `toast` (already used in all mutation hooks) | Already integrated project-wide |
| Optimistic updates | Manual state management | React Query `onMutate`/`onError` pattern (already used in `useUpdateDecision`) | Proven pattern with rollback support |

**Key insight:** Every UI pattern needed already exists in the project. The work is composing existing building blocks, not building new infrastructure.

## Common Pitfalls

### Pitfall 1: N+1 Queries in Report Endpoint
**What goes wrong:** Building the report by iterating through members and making individual queries per contact for stage events, decisions, and next steps.
**Why it happens:** Natural to loop and count, but generates O(n) queries.
**How to avoid:** Use Django aggregation (`Count`, `Sum`, `Subquery`) to compute all metrics in a few SQL queries. Follow the pattern in `JournalContactListCreateView.get_queryset()` which uses `Prefetch` to avoid N+1.
**Warning signs:** Report load time > 500ms for journals with 50+ contacts.

### Pitfall 2: Stale Grid After Stage Toggle
**What goes wrong:** User clicks stage checkbox, event is created server-side, but grid still shows the old unchecked state until page refresh.
**Why it happens:** Not invalidating the correct query keys after mutation.
**How to avoid:** In the stage toggle mutation, invalidate `["journals", journalId, "members"]` to refetch the full members list with updated `stage_events` summaries. Consider optimistic update to make the checkbox appear checked immediately.
**Warning signs:** Checkbox doesn't visually change on click, or changes then reverts.

### Pitfall 3: Decision Column Misalignment
**What goes wrong:** Moving the Decision column breaks the grid's sticky header alignment or the column widths don't match.
**Why it happens:** The current grid uses `PIPELINE_STAGES.map()` for stage columns with fixed widths, then manually adds Decision and NextSteps columns. Inserting Decision mid-loop requires breaking the loop.
**How to avoid:** Define a column configuration array that includes both stage columns and the Decision column in the correct order. Render from this configuration instead of iterating PIPELINE_STAGES.
**Warning signs:** Column headers don't align with data, or horizontal scroll is broken.

### Pitfall 4: Date Range Filter Doesn't Reset Stale Data
**What goes wrong:** Changing date range doesn't refetch report data because React Query serves stale cache.
**Why it happens:** Query key doesn't include date range params.
**How to avoid:** Include date params in the query key: `["journals", journalId, "report", dateParams]`. Per MEMORY.md: "Pass clean `Record<string, string>` (from `toQueryParams()`) as query keys, not objects with `undefined` values."
**Warning signs:** Changing date range shows same data.

### Pitfall 5: Existing EventTimelineDrawer Still Opens on Stage Click
**What goes wrong:** After implementing instant toggle, clicking a checked stage still opens the drawer via the old `onStageCellClick` callback.
**Why it happens:** Two behaviors need to coexist: unchecked stages get auto-created events, checked stages can still be clicked to view event details.
**How to avoid:** Branch the click handler: if `!eventSummary.has_events`, auto-create event; if `eventSummary.has_events`, open drawer.
**Warning signs:** Every click creates a duplicate event, or the drawer never opens for viewing existing events.

### Pitfall 6: Stage Event Creation Requires journal_contact ID, Not contact ID
**What goes wrong:** The `StageCell` currently only receives `contactId` (the raw Contact UUID), not the `journalContactId` (the JournalContact through-table UUID).
**Why it happens:** The grid passes `member.contact` to `StageCell`, not `member.id`.
**How to avoid:** Pass `journalContactId={member.id}` to `StageCell` as a new prop, so it can call `createStageEvent({ journal_contact: journalContactId, ... })` directly.
**Warning signs:** 400 error from API when trying to create stage event.

## Code Examples

### Existing Pattern: Optimistic Mutation with Rollback
```typescript
// Source: frontend/src/hooks/useJournals.ts (useUpdateDecision)
// This exact pattern should be replicated for the stage toggle mutation
export function useToggleStageEvent(journalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: StageEventCreate) => createStageEvent(data),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({
        queryKey: ["journals", journalId, "members"],
      })
      const previous = queryClient.getQueryData(["journals", journalId, "members", {}])
      // Optimistically update stage_events for the member
      // ... (update cache to show checkbox as checked)
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["journals", journalId, "members", {}], context.previous)
      }
      toast.error("Failed to log stage event")
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["journals", journalId, "members"] })
    },
  })
}
```

### Existing Pattern: DateRangePicker Integration
```typescript
// Source: frontend/src/pages/admin/analytics/AdminAnalyticsDashboard.tsx
// Reuse this exact pattern for the journal report
const [dateRange, setDateRange] = useState<DateRange | null>(null)
const dateParams = dateRangeToParams(dateRange)
const { data, isLoading } = useJournalReport(journalId, dateParams)

// In JSX:
<DateRangePicker value={dateRange} onChange={setDateRange} />
```

### Existing Pattern: Chart with shadcn ChartContainer
```typescript
// Source: frontend/src/pages/journals/components/ReportCharts.tsx
// Follow this exact pattern for new charts
<ChartContainer config={chartConfig} className="min-h-[300px] w-full">
  <BarChart data={data}>
    <CartesianGrid vertical={false} />
    <XAxis dataKey="stage" tickLine={false} tickMargin={10} axisLine={false} />
    <YAxis />
    <ChartTooltip content={<ChartTooltipContent />} />
    <Bar dataKey="count" fill="var(--color-count)" radius={4} />
  </BarChart>
</ChartContainer>
```

### Existing Pattern: Conditional Alert Section
```typescript
// Pattern from admin analytics AlertsPanel
{data.alerts.stalled_contacts > 0 && (
  <Card className="border-warning">
    <CardHeader className="pb-2">
      <CardTitle className="text-sm font-medium flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-warning" />
        Stalled Contacts
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-muted-foreground">
        {data.alerts.stalled_contacts} contact(s) have had no activity in the last 30 days
      </p>
    </CardContent>
  </Card>
)}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 4 separate analytics API calls | Single aggregated report endpoint | This phase | Fewer network requests, simpler loading state |
| Stage click opens drawer (read-only checkbox) | Stage click auto-creates event (instant toggle) | This phase | Faster workflow for missionaries |
| Decision column at end of grid | Decision column between Close and Thank | This phase | Matches donor pipeline mental model |
| PipelineBreakdownChart in reports | Removed per JRNL-06 | This phase | Cleaner report focused on activity |

## Open Questions

1. **Default event type for auto-created stage events**
   - What we know: Each stage needs a default `event_type` when auto-created via checkbox click. The `StageEventType` choices include natural defaults (e.g., `call_logged` for Contact, `meeting_completed` for Meet, `ask_made` for Close).
   - What's unclear: Whether the user expects a specific mapping or if a generic `other` type is acceptable for all stages.
   - Recommendation: Use stage-specific defaults as shown in Pattern 2 above. This provides meaningful event records without requiring user input.

2. **Stalled contacts threshold**
   - What we know: "Stalled" means no recent activity. Admin analytics uses a configurable threshold.
   - What's unclear: What the exact day threshold should be (14, 30, 60 days?).
   - Recommendation: Use 30 days as the default. This is a reasonable threshold for donor engagement and matches common CRM patterns.

3. **Report date range: does it scope metric cards or only charts?**
   - What we know: User wants a date range picker with presets. Reports show "what the missionary has been doing."
   - What's unclear: Should "Total Contacts" change with date range (contacts added during range) or always show current total?
   - Recommendation: Total Contacts = always-current count (it's a snapshot, not time-based). With Decisions, Confirmed $, Pending = filtered by date range. Charts = filtered by date range. Alerts = always-current (stalled is about current state).

4. **Existing DecisionTrends/StageActivity/NextStepsQueue components**
   - What we know: These will be replaced in the report tab. They're imported in `JournalDetail.tsx` and exported from the barrel.
   - What's unclear: Are they used anywhere else?
   - Recommendation: Check for other imports before removing. If only used in journal report, they can be deleted after the rebuild. If used elsewhere, keep them.

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** -- all architecture patterns, file locations, component APIs, and hook implementations verified by reading the actual source code
- **`frontend/src/pages/journals/`** -- complete journal page component tree
- **`apps/journals/`** -- complete backend models, views, serializers, URLs
- **`frontend/src/components/ui/`** -- shadcn component library (chart, date-range-picker, progress, card)
- **`frontend/src/hooks/useJournals.ts`** -- all journal React Query hooks
- **`frontend/src/api/journals.ts`** -- all journal API functions
- **`frontend/src/types/journals.ts`** -- all TypeScript types and constants

### Secondary (MEDIUM confidence)
- **Recharts API** -- patterns verified from existing project usage (ReportCharts.tsx, MonthlyGiftsCard.tsx, etc.), Recharts v3 API is consistent with observed usage

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies needed
- Architecture: HIGH -- patterns verified from existing codebase, all building blocks exist
- Pitfalls: HIGH -- identified from actual code reading (N+1 queries, stale cache, prop threading)

**Research date:** 2026-02-27
**Valid until:** 2026-03-27 (stable domain, no external dependency changes expected)
