# Phase 55: Add Scheduled Pipeline Stage to Journal System - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a "Scheduled" pipeline stage between Contact and Meet in the journal system. This represents "a meeting has been scheduled with this donor." Full pipeline stage with event logging, date/time metadata, calendar icon display, and analytics inclusion. No changes to Goal, Dashboard, Decision, NextStep, View As, or permissions.

</domain>

<decisions>
## Implementation Decisions

### Stage position and identity
- **D-01:** Scheduled is inserted between Contact and Meet — grid shows 7 columns: Contact → Scheduled → Meet → Close → Decision → Thank → Next Steps
- **D-02:** Stage value: `scheduled` (TextChoices enum, matching existing convention)
- **D-03:** Event type: `meeting_scheduled` is the only event type for this stage

### Cell display
- **D-04:** Checked cell shows a calendar icon (Lucide) + compact date label in "Mar 25" format (short month + day, no time)
- **D-05:** Empty cell shows a faded calendar icon (not the empty square used by other stages)
- **D-06:** When multiple scheduled events exist for a contact, the cell displays the most recent scheduled date
- **D-07:** No past-date styling — date label stays neutral regardless of whether the date has passed

### Stage transition behavior
- **D-08:** Scheduled is treated as optional — skipping from Contact → Meet does not trigger a "skipped stage" warning
- **D-09:** Other stage skip warnings remain unchanged

### Click behavior and event logging
- **D-10:** Clicking an empty Scheduled cell always opens the Log Event dialog (no one-click auto-create like other stages) because date input is required
- **D-11:** Dialog shows: date picker (required), time picker (optional), notes field
- **D-12:** Event type is pre-set to `meeting_scheduled` (only valid type for this stage)
- **D-13:** Date and time stored in metadata JSONField as `{"scheduled_date": "YYYY-MM-DD", "scheduled_time": "HH:MM"}`

### Metadata storage
- **D-14:** JournalStageEvent gets a nullable JSONField (`metadata`) with `default=None, blank=True, null=True` — other stages don't need it
- **D-15:** When stage is `scheduled`, metadata must contain `scheduled_date` (required); `scheduled_time` is optional
- **D-16:** Additive migration only — no transformation of existing records

### Goal exclusion
- **D-17:** Scheduled stage and `meeting_scheduled` event type must NOT count toward goal calls_count or meetings_count — verify existing filter logic and confirm exclusion

### Analytics
- **D-18:** Scheduled stage included in all per-stage analytics displays (pipeline-breakdown, stage-activity, journal-report charts)

### Claude's Discretion
- Date picker and time picker component choice (existing component library)
- Exact icon styling and faded opacity level for empty cell
- Migration numbering
- Serializer validation implementation details
- How to handle the optional skip in `checkStageTransition()` (exclusion list vs. flag)

</decisions>

<specifics>
## Specific Ideas

- Calendar icon should be visually distinct from the checkmark badges used by other stage cells — this is a date-based stage, not just a yes/no toggle
- Faded calendar icon on empty cells hints "click here to schedule" — different from the empty squares on other stages

</specifics>

<canonical_refs>
## Canonical References

### Full implementation spec
- `prompts/scheduled_column_prompt.md` — Detailed requirements, acceptance criteria, regression checklist, and "what NOT to change" guardrails

### Backlog source
- `.planning/todos/pending/2026-03-21-add-scheduled-column-to-journal-pipeline.md` — Original todo with file list and problem statement (source: GitHub Issue #25)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PipelineStage` TextChoices enum in `apps/journals/models.py` — add `SCHEDULED = 'scheduled'` between CONTACT and MEET
- `JournalStageEvent` model already has the event log pattern — metadata JSONField is new but follows existing nullable field patterns
- `StageCell` component (`frontend/src/pages/journals/components/StageCell.tsx`) — needs conditional behavior for scheduled (open dialog instead of auto-create)
- `LogEventDialog` component — needs date/time picker fields when stage is scheduled
- `EventTimelineDrawer` — needs to render scheduled_date/time from metadata
- `PIPELINE_STAGES` array and `STAGE_ORDER` map in `frontend/src/types/journals.ts` — add 'scheduled' at index 1
- `checkStageTransition()` in `frontend/src/types/journals.ts` — needs optional-stage exemption for scheduled

### Established Patterns
- Stage cells use `React.memo()` with custom comparison for performance
- Default event types per stage defined in `StageCell.tsx` (lines 36-46)
- `getFreshnessColor()` for badge coloring based on event recency
- Append-only event log — JournalStageEvents are immutable records
- Goal services in `apps/users/goal_services.py` count calls/meetings by filtering specific stages — verify scheduled is excluded

### Integration Points
- `JournalGrid.tsx` renders columns from stage list — `STAGES_BEFORE_DECISION` array needs scheduled added
- `ReportCharts.tsx` renders per-stage data in bar charts — needs scheduled in color map
- Analytics views (`views.py` lines 489-719) aggregate by stage — will include scheduled automatically if stage exists in choices
- `DecisionCell` positioned between Close and Thank — grid layout logic separates stages into before/after decision groups

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 55-add-scheduled-pipeline-stage-to-journal-system*
*Context gathered: 2026-03-21*
