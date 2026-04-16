# Phase 55: Add Scheduled Pipeline Stage to Journal System - Research

**Researched:** 2026-03-21
**Domain:** Django backend (models, serializers, views) + React frontend (journal grid, dialogs, analytics)
**Confidence:** HIGH

## Summary

This phase adds a "Scheduled" pipeline stage between Contact and Meet in the journal system. The existing codebase is well-structured for this change: `PipelineStage` is a TextChoices enum, the frontend reads stage lists from constants, and the metadata JSONField already exists on `JournalStageEvent`. The primary work is (1) adding the enum value + migration, (2) modifying the frontend `StageCell` to show a calendar icon and open a dialog with date/time pickers instead of auto-creating events, (3) updating the `LogEventDialog` to support date/time fields for the scheduled stage, (4) updating analytics/chart components to include the new stage, and (5) verifying goal exclusion.

A critical discovery: the `metadata` JSONField **already exists** on `JournalStageEvent` with `default=dict, blank=True`. The CONTEXT.md D-14 specified adding it with `default=None, null=True` -- but since it already exists with `default=dict`, no migration is needed for the metadata field. The migration only needs to update the `stage` field choices (and technically, `meeting_scheduled` already exists in `StageEventType`). The serializer already includes metadata in read/write.

**Primary recommendation:** Add `SCHEDULED = 'scheduled'` to `PipelineStage` enum between CONTACT and MEET, create a migration for the choices change, then systematically update every frontend constant/component/chart that references the stage list.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Scheduled is inserted between Contact and Meet -- grid shows 7 columns: Contact -> Scheduled -> Meet -> Close -> Decision -> Thank -> Next Steps
- **D-02:** Stage value: `scheduled` (TextChoices enum, matching existing convention)
- **D-03:** Event type: `meeting_scheduled` is the only event type for this stage
- **D-04:** Checked cell shows a calendar icon (Lucide) + compact date label in "Mar 25" format (short month + day, no time)
- **D-05:** Empty cell shows a faded calendar icon (not the empty square used by other stages)
- **D-06:** When multiple scheduled events exist for a contact, the cell displays the most recent scheduled date
- **D-07:** No past-date styling -- date label stays neutral regardless of whether the date has passed
- **D-08:** Scheduled is treated as optional -- skipping from Contact -> Meet does not trigger a "skipped stage" warning
- **D-09:** Other stage skip warnings remain unchanged
- **D-10:** Clicking an empty Scheduled cell always opens the Log Event dialog (no one-click auto-create like other stages) because date input is required
- **D-11:** Dialog shows: date picker (required), time picker (optional), notes field
- **D-12:** Event type is pre-set to `meeting_scheduled` (only valid type for this stage)
- **D-13:** Date and time stored in metadata JSONField as `{"scheduled_date": "YYYY-MM-DD", "scheduled_time": "HH:MM"}`
- **D-14:** JournalStageEvent gets a nullable JSONField (`metadata`) with `default=None, blank=True, null=True` -- **NOTE: field already exists with `default=dict, blank=True` -- no migration needed for this**
- **D-15:** When stage is `scheduled`, metadata must contain `scheduled_date` (required); `scheduled_time` is optional
- **D-16:** Additive migration only -- no transformation of existing records
- **D-17:** Scheduled stage and `meeting_scheduled` event type must NOT count toward goal calls_count or meetings_count -- verify existing filter logic and confirm exclusion
- **D-18:** Scheduled stage included in all per-stage analytics displays (pipeline-breakdown, stage-activity, journal-report charts)

### Claude's Discretion
- Date picker and time picker component choice (existing component library)
- Exact icon styling and faded opacity level for empty cell
- Migration numbering
- Serializer validation implementation details
- How to handle the optional skip in `checkStageTransition()` (exclusion list vs. flag)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Architecture Patterns

### Change Inventory

The scheduled stage touches these files, organized by layer:

#### Backend (Django)
| File | Change | Complexity |
|------|--------|------------|
| `apps/journals/models.py` | Add `SCHEDULED = 'scheduled', 'Scheduled'` to `PipelineStage` between CONTACT and MEET | Trivial |
| `apps/journals/models.py` | No change to `StageEventType` -- `MEETING_SCHEDULED` already exists | None |
| `apps/journals/models.py` | No change to `metadata` field -- already exists with `default=dict` | None |
| `apps/journals/migrations/0004_*.py` | New migration for PipelineStage choices update (CharField choices only) | Trivial |
| `apps/journals/serializers.py` | Add validation in `JournalStageEventSerializer`: when stage='scheduled', require `metadata.scheduled_date` | Small |
| `apps/journals/serializers.py` | Add `scheduled_date` to `get_stage_events` summary for scheduled stage (extract from metadata of most recent event) | Small |
| `apps/journals/views.py` | Update `stage_activity` hardcoded dict to include `'scheduled': 0` in `by_month` default | Trivial |
| `apps/users/goal_services.py` | VERIFY ONLY -- calls_count filters `event_type='call_logged'`, meetings_count filters `event_type='meeting_completed'` -- `meeting_scheduled` is already excluded | None |
| `apps/insights/services.py` | `get_conversion_funnel` iterates `PipelineStage` enum -- auto-includes scheduled | None |

#### Frontend (React/TypeScript)
| File | Change | Complexity |
|------|--------|------------|
| `frontend/src/types/journals.ts` | Add `'scheduled'` to `PipelineStage` type, `STAGE_LABELS`, `PIPELINE_STAGES`, `STAGE_ORDER`, `StageActivityItem` | Small |
| `frontend/src/types/journals.ts` | Update `checkStageTransition()` to exclude `scheduled` from skip warnings | Small |
| `frontend/src/types/journals.ts` | Add `scheduled_date` to `StageEventSummary` interface | Trivial |
| `frontend/src/pages/journals/components/StageCell.tsx` | Conditional rendering for scheduled: calendar icon (filled/faded), open dialog instead of auto-create, show date label | Medium |
| `frontend/src/pages/journals/components/StageCell.tsx` | Update `getDefaultEventType` to include scheduled: `'meeting_scheduled'` | Trivial |
| `frontend/src/pages/journals/components/StageCell.tsx` | Update `getHighestStageWithEvents` to include `'scheduled'` in reverse order | Trivial |
| `frontend/src/pages/journals/components/JournalGrid.tsx` | Add `'scheduled'` to `STAGES_BEFORE_DECISION` array | Trivial |
| `frontend/src/pages/journals/components/LogEventDialog.tsx` | Add conditional date picker + time picker fields when stage is `'scheduled'`; lock event type to `meeting_scheduled`; send metadata | Medium |
| `frontend/src/pages/journals/components/EventTimelineDrawer.tsx` | Display `scheduled_date`/`scheduled_time` from metadata in a user-friendly format | Small |
| `frontend/src/pages/journals/components/ReportCharts.tsx` | Add `scheduled` to `stageChartConfig` and `STAGE_COLOR_MAP` | Trivial |
| `frontend/src/api/journals.ts` | No changes needed -- `StageEventCreate` already has `metadata?: Record<string, unknown>` | None |

### Existing Pattern: Stage Cell Behavior

Current StageCell has two states:
1. **No events**: Renders `<Square>` icon, click auto-creates event with default event type
2. **Has events**: Renders `<Check>` Badge with freshness color, click deletes events (uncheck)

The scheduled stage needs a third behavior variant:
1. **No events**: Renders faded `<CalendarDays>` icon, click opens LogEventDialog (not auto-create)
2. **Has events**: Renders `<CalendarDays>` icon with date label (e.g. "Mar 25"), click opens EventTimelineDrawer (or deletes -- follow existing pattern for consistency)

### Pattern: Stage Summary with Metadata

The `get_stage_events` serializer method builds per-stage summaries. For the scheduled stage, the summary needs an additional field: `scheduled_date` extracted from the most recent event's metadata. This keeps the grid rendering efficient (no extra API call).

```python
# In get_stage_events, after building the base summary:
if stage == 'scheduled' and stage_events:
    last_metadata = stage_events[0].metadata or {}
    summaries[stage]['scheduled_date'] = last_metadata.get('scheduled_date')
```

### Pattern: Conditional Dialog Fields

The LogEventDialog currently has: stage selector, event type selector, notes textarea. For the scheduled stage:
- Stage is pre-set and locked to `'scheduled'`
- Event type is pre-set and locked to `'meeting_scheduled'`
- Date picker (required) added above notes
- Time input (optional) added below date picker
- On submit, `metadata: { scheduled_date, scheduled_time }` is included in the API payload

### Pattern: Optional Stage Skip

`checkStageTransition()` in `journals.ts` computes skipped stages based on `STAGE_ORDER`. Two approaches:

**Option A: Exclusion list** (recommended -- simpler, more explicit):
```typescript
const OPTIONAL_STAGES: PipelineStage[] = ['scheduled']

// In checkStageTransition, filter optional stages out of skipped list:
const skipped = Object.entries(STAGE_ORDER)
  .filter(([stage, order]) =>
    order > currentOrder &&
    order < targetOrder &&
    !OPTIONAL_STAGES.includes(stage as PipelineStage)
  )
  .map(([stage]) => STAGE_LABELS[stage as PipelineStage])
```

**Option B: Flag on stage definition** -- more complex, not needed for one optional stage.

Recommendation: Use Option A (exclusion list).

### Recommended Implementation Order

```
Wave 1: Backend model + migration + serializer validation
Wave 2: Frontend types + constants + StageCell + JournalGrid
Wave 3: LogEventDialog date/time fields + API integration
Wave 4: EventTimelineDrawer metadata display + analytics charts
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date picker UI | Custom date input | shadcn/ui `Calendar` + `Popover` (already in project as `date-range-picker.tsx`) | react-day-picker 9.13.2 already installed; Calendar component exists |
| Time input | Custom time widget | Native `<input type="time">` styled with shadcn/ui Input class | Time picker libraries add complexity; HTML5 time input is sufficient for "HH:MM" |
| Date formatting | Manual string manipulation | `date-fns` `format()` (already installed v4.1.0) | Consistent with existing codebase pattern |
| Calendar icon | Custom SVG | Lucide React `CalendarDays` icon | Consistent with project icon system; distinct from `Calendar` used in date-range-picker |

## Existing Assets (No Changes Needed)

These items already support the scheduled stage without modification:

| Asset | Why No Change |
|-------|---------------|
| `StageEventType.MEETING_SCHEDULED` | Already exists in `models.py` (line 34) |
| `JournalStageEvent.metadata` JSONField | Already exists with `default=dict, blank=True` (line 186-190) |
| `JournalStageEventSerializer.fields` | Already includes `metadata` in read/write (line 207) |
| `StageEventCreate.metadata` in `api/journals.ts` | Already typed as `Record<string, unknown>` (line 142) |
| `StageEvent.metadata` in `types/journals.ts` | Already typed as `Record<string, unknown>` (line 92) |
| `EventTimelineDrawer` metadata rendering | Already renders metadata key-value pairs (lines 214-220) |
| `get_conversion_funnel()` in insights | Iterates `PipelineStage` enum automatically (line 574) |
| `goal_services.py` calls/meetings counts | Filters by specific event_types (`call_logged`, `meeting_completed`) -- `meeting_scheduled` excluded (lines 82-89) |

## Common Pitfalls

### Pitfall 1: Hardcoded Stage Lists
**What goes wrong:** Multiple places have hardcoded stage lists/dicts that won't automatically include the new stage.
**Why it happens:** Not all code iterates the PipelineStage enum; some places use literal dicts.
**How to avoid:** Search for all hardcoded stage references and update each one.
**Known hardcoded locations:**
- `views.py` line 530-532: `stage_activity` has hardcoded `by_month` default dict with 6 stages
- `ReportCharts.tsx` lines 46-54: `stageChartConfig` lists 6 stages
- `ReportCharts.tsx` lines 56-64: `STAGE_COLOR_MAP` lists 6 stages
- `StageCell.tsx` lines 23-24: `getHighestStageWithEvents` has hardcoded reverse stage list
- `StageCell.tsx` lines 37-45: `getDefaultEventType` has hardcoded stage-to-event map
- `types/journals.ts` line 296-303: `StageActivityItem` interface has 6 stage count fields

### Pitfall 2: D-14 Metadata Field Already Exists
**What goes wrong:** Creating a migration to add a `metadata` field that already exists causes `django.db.utils.OperationalError: column already exists`.
**Why it happens:** The CONTEXT.md was written before inspecting the model and assumed the field didn't exist.
**How to avoid:** The migration should ONLY update the `stage` field choices. Do NOT attempt to add/alter the metadata field.
**Warning signs:** Migration file containing `AddField(name='metadata')`.

### Pitfall 3: StageCell Click Behavior Divergence
**What goes wrong:** The scheduled StageCell needs different click behavior (open dialog) than all other stages (auto-create/delete). Implementing this as special-case logic in StageCell can become messy.
**Why it happens:** Current StageCell treats all stages identically.
**How to avoid:** Use a clean conditional branch at the top of `handleClick` -- if `stage === 'scheduled'`, call a callback prop (e.g., `onScheduledClick`) that opens the LogEventDialog. Keep the existing auto-create/delete path for other stages.

### Pitfall 4: Stage Order Renumbering
**What goes wrong:** Inserting `scheduled` at position 2 shifts all subsequent stage orders (meet: 2->3, close: 3->4, etc.), which could break `checkStageTransition` for existing contacts whose "highest stage" was computed with old ordering.
**Why it happens:** `STAGE_ORDER` is used for transition checking only -- no data is persisted with these numbers.
**How to avoid:** Update `STAGE_ORDER` to: `contact:1, scheduled:2, meet:3, close:4, decision:5, thank:6, next_steps:7`. Since the order is recalculated on every render from current event data, the renumbering is safe -- no stored data uses these numbers.

### Pitfall 5: Summary Missing scheduled_date for Grid Display
**What goes wrong:** The grid cell needs to display "Mar 25" but the stage event summary from the API doesn't include the scheduled_date from metadata.
**Why it happens:** `get_stage_events` in the serializer doesn't extract metadata fields into the summary.
**How to avoid:** Extend the summary dict for the `scheduled` stage to include `scheduled_date` from the most recent event's metadata. The frontend `StageEventSummary` type also needs this optional field added.

### Pitfall 6: LogEventDialog Submit Must Include Metadata
**What goes wrong:** The dialog creates an event without metadata, so scheduled_date is lost.
**Why it happens:** Current `handleSubmit` doesn't pass metadata to `createStageEvent`.
**How to avoid:** When stage is `scheduled`, construct `metadata: { scheduled_date: selectedDate, scheduled_time: selectedTime || undefined }` and include it in the `createStageEvent` call.

## Code Examples

### Backend: PipelineStage Enum Update

```python
# apps/journals/models.py
class PipelineStage(models.TextChoices):
    """Seven-stage donor engagement pipeline."""
    CONTACT = 'contact', 'Contact'
    SCHEDULED = 'scheduled', 'Scheduled'  # NEW -- between Contact and Meet
    MEET = 'meet', 'Meet'
    CLOSE = 'close', 'Close'
    DECISION = 'decision', 'Decision'
    THANK = 'thank', 'Thank'
    NEXT_STEPS = 'next_steps', 'Next Steps'
```

### Backend: Serializer Validation for Scheduled Stage

```python
# apps/journals/serializers.py -- JournalStageEventSerializer.validate()
def validate(self, attrs):
    if not attrs.get('journal_contact') and not attrs.get('contact_id'):
        raise serializers.ValidationError(
            "Either journal_contact or contact_id is required."
        )

    # Validate scheduled stage requires scheduled_date in metadata
    if attrs.get('stage') == 'scheduled':
        metadata = attrs.get('metadata') or {}
        if not metadata.get('scheduled_date'):
            raise serializers.ValidationError({
                'metadata': 'scheduled_date is required when stage is scheduled.'
            })

    return attrs
```

### Backend: Stage Summary with scheduled_date

```python
# apps/journals/serializers.py -- JournalContactSerializer.get_stage_events()
# After building the summary for a stage:
if stage == 'scheduled' and stage_events:
    last_metadata = stage_events[0].metadata or {}
    summaries[stage]['scheduled_date'] = last_metadata.get('scheduled_date')
else:
    summaries[stage]['scheduled_date'] = None
```

### Backend: stage_activity View Fix

```python
# apps/journals/views.py -- stage_activity action
by_month = defaultdict(lambda: {
    'contact': 0, 'scheduled': 0, 'meet': 0, 'close': 0,
    'decision': 0, 'thank': 0, 'next_steps': 0
})
```

### Frontend: Updated Types

```typescript
// frontend/src/types/journals.ts
export type PipelineStage =
  | 'contact'
  | 'scheduled'  // NEW
  | 'meet'
  | 'close'
  | 'decision'
  | 'thank'
  | 'next_steps'

export const STAGE_LABELS: Record<PipelineStage, string> = {
  contact: 'Contact',
  scheduled: 'Scheduled',  // NEW
  meet: 'Meet',
  close: 'Close',
  decision: 'Decision',
  thank: 'Thank',
  next_steps: 'Next Steps',
}

export const PIPELINE_STAGES: PipelineStage[] = [
  'contact',
  'scheduled',  // NEW
  'meet',
  'close',
  'decision',
  'thank',
  'next_steps',
]

export const STAGE_ORDER: Record<PipelineStage, number> = {
  contact: 1,
  scheduled: 2,  // NEW
  meet: 3,       // was 2
  close: 4,      // was 3
  decision: 5,   // was 4
  thank: 6,      // was 5
  next_steps: 7, // was 6
}
```

### Frontend: Optional Stage Skip

```typescript
// frontend/src/types/journals.ts -- checkStageTransition()
const OPTIONAL_STAGES: PipelineStage[] = ['scheduled']

export function checkStageTransition(
  currentStage: PipelineStage | null,
  targetStage: PipelineStage
): StageTransitionCheck {
  if (!currentStage) {
    return { isSequential: true, skippedStages: [], isRevisiting: false }
  }

  const currentOrder = STAGE_ORDER[currentStage]
  const targetOrder = STAGE_ORDER[targetStage]

  if (targetOrder < currentOrder) {
    return { isSequential: false, skippedStages: [], isRevisiting: true }
  }

  if (targetOrder > currentOrder + 1) {
    const skipped = Object.entries(STAGE_ORDER)
      .filter(([stage, order]) =>
        order > currentOrder &&
        order < targetOrder &&
        !OPTIONAL_STAGES.includes(stage as PipelineStage)
      )
      .map(([stage]) => STAGE_LABELS[stage as PipelineStage])
    return {
      isSequential: skipped.length === 0,  // sequential if only optional stages skipped
      skippedStages: skipped,
      isRevisiting: false,
    }
  }

  return { isSequential: true, skippedStages: [], isRevisiting: false }
}
```

### Frontend: StageCell Scheduled Variant

```typescript
// Conceptual pattern for StageCell scheduled cell rendering
// Empty state (no events):
<button onClick={() => onScheduledClick(journalContactId)} ...>
  <CalendarDays className="h-5 w-5 text-muted-foreground/40" />
</button>

// Has events state:
<button onClick={handleClick} ...>
  <div className="flex flex-col items-center gap-0.5">
    <CalendarDays className="h-4 w-4 text-primary" />
    <span className="text-[10px] text-muted-foreground leading-none">
      {format(parseISO(scheduledDate), 'MMM d')}
    </span>
  </div>
</button>
```

### Frontend: Date Picker in LogEventDialog

```typescript
// Uses existing Calendar component + Popover pattern from date-range-picker.tsx
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

// When stage === 'scheduled':
<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline" className={cn(!date && "text-muted-foreground")}>
      <CalendarDays className="mr-2 h-4 w-4" />
      {date ? format(date, 'PPP') : 'Pick a date'}
    </Button>
  </PopoverTrigger>
  <PopoverContent className="w-auto p-0">
    <Calendar mode="single" selected={date} onSelect={setDate} />
  </PopoverContent>
</Popover>

// Time input (optional):
<Input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
```

## Goal Exclusion Verification

**Verified: Scheduled stage is ALREADY excluded from goal metrics.** (HIGH confidence)

In `apps/users/goal_services.py`:
- `calls_count` filters by `event_type='call_logged'` (line 83)
- `meetings_count` filters by `event_type='meeting_completed'` (line 87)

The `meeting_scheduled` event type is NOT matched by either filter. No code change needed. The planner should include a verification step confirming this after implementation.

## Analytics Integration

**Backend analytics views that need the `scheduled` stage added:**

1. `stage_activity` (views.py line 530) -- hardcoded `by_month` default dict needs `'scheduled': 0`
2. `pipeline_breakdown` (views.py line 544) -- no change needed (uses Subquery, auto-includes new stage)
3. `journal_report` (views.py line 651-665) -- no change needed (uses Subquery)
4. `get_conversion_funnel` (insights/services.py line 574) -- no change needed (iterates `PipelineStage` enum)

**Frontend analytics components that need updating:**

1. `ReportCharts.tsx` -- `stageChartConfig` and `STAGE_COLOR_MAP` need `scheduled` entry
2. `StageActivityItem` type in `journals.ts` -- needs `scheduled: number` field

## Date Picker Component Strategy

**Use existing components** (HIGH confidence):

- `Calendar` component (`frontend/src/components/ui/calendar.tsx`) wraps react-day-picker 9.13.2
- `Popover` component exists for dropdown calendar
- Pattern already established in `DateRangePicker` component
- For single-date selection: use `Calendar` with `mode="single"` instead of `mode="range"`
- For time: use `<Input type="time" />` -- no library needed for "HH:MM" input

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + Django TestCase (backend); no frontend tests |
| Config file | `pytest.ini` at project root |
| Quick run command | `python manage.py test apps.journals --verbosity=1` |
| Full suite command | `python manage.py test --verbosity=1` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-02 | `scheduled` is a valid PipelineStage value | unit | `python manage.py test apps.journals.tests -k scheduled` | No -- Wave 0 |
| D-03 | Event with stage=scheduled + event_type=meeting_scheduled creates successfully | unit | `python manage.py test apps.journals.tests -k scheduled_event` | No -- Wave 0 |
| D-13 | Metadata contains scheduled_date when stage=scheduled | unit | `python manage.py test apps.journals.tests -k metadata` | No -- Wave 0 |
| D-15 | Validation rejects stage=scheduled without scheduled_date in metadata | unit | `python manage.py test apps.journals.tests -k validation` | No -- Wave 0 |
| D-17 | Goal counts exclude meeting_scheduled events | unit | Existing goal tests + new assertion | Partial |

### Wave 0 Gaps
- [ ] `apps/journals/tests/test_scheduled_stage.py` -- covers D-02, D-03, D-13, D-15
- [ ] Assertion in goal service tests verifying `meeting_scheduled` exclusion (D-17)

## Open Questions

1. **StageCell click behavior for checked scheduled cell**
   - What we know: Empty cell opens dialog (D-10). Other stages delete events on click (uncheck).
   - What's unclear: Should clicking a checked scheduled cell also delete events (uncheck), or should it open the timeline drawer?
   - Recommendation: Follow existing pattern -- clicking a checked cell deletes events (uncheck). The timeline drawer is accessible from elsewhere. This keeps the mental model consistent across all stages.

2. **Chart color for scheduled stage**
   - What we know: Six chart colors (`--chart-1` through `--chart-6`) are used for the six existing stages.
   - What's unclear: There may not be a `--chart-7` CSS variable defined.
   - Recommendation: Check if `--chart-7` exists. If not, either define it or use a distinct HSL value. Alternatively, reuse an unused color slot or use `hsl(var(--chart-2))` shifted slightly since scheduled sits between contact and meet.

## Sources

### Primary (HIGH confidence)
- `apps/journals/models.py` -- Current PipelineStage enum, StageEventType enum, JournalStageEvent model (metadata field exists)
- `apps/journals/serializers.py` -- JournalStageEventSerializer (metadata already in fields), get_stage_events summary builder
- `apps/journals/views.py` -- stage_activity hardcoded dict, pipeline_breakdown/journal_report (auto-include)
- `apps/users/goal_services.py` -- calls_count/meetings_count filter by specific event_types (meeting_scheduled excluded)
- `apps/insights/services.py` -- get_conversion_funnel iterates PipelineStage enum
- `frontend/src/types/journals.ts` -- PipelineStage type, STAGE_ORDER, PIPELINE_STAGES, checkStageTransition
- `frontend/src/pages/journals/components/StageCell.tsx` -- Current two-state cell behavior
- `frontend/src/pages/journals/components/LogEventDialog.tsx` -- Current dialog structure
- `frontend/src/pages/journals/components/JournalGrid.tsx` -- STAGES_BEFORE_DECISION array
- `frontend/src/pages/journals/components/ReportCharts.tsx` -- Hardcoded stage configs
- `frontend/src/pages/journals/components/EventTimelineDrawer.tsx` -- Metadata already rendered
- `frontend/src/components/ui/calendar.tsx` -- react-day-picker 9.13.2 wrapper
- `frontend/src/api/journals.ts` -- StageEventCreate already supports metadata
- `package.json` -- react-day-picker 9.13.2, date-fns 4.1.0 confirmed

### Secondary (MEDIUM confidence)
- `prompts/scheduled_column_prompt.md` -- Detailed acceptance criteria and regression checklist
- `.planning/todos/pending/2026-03-21-add-scheduled-column-to-journal-pipeline.md` -- Original problem statement

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components already in project (Calendar, Popover, date-fns, Lucide icons)
- Architecture: HIGH -- clear pattern from existing stage implementation, all files identified and inspected
- Pitfalls: HIGH -- six specific pitfalls documented with prevention strategies based on actual code inspection

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable domain, no external dependency changes expected)
