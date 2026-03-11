---
phase: 40-journal-report-grid-behavior
plan: 02
subsystem: ui
tags: [react, journal-grid, stage-events, checkbox-toggle, pipeline]

# Dependency graph
requires:
  - phase: 40-journal-report-grid-behavior
    provides: "Journal grid foundation with stage columns, DecisionCell, StageCell components"
provides:
  - "Decision column repositioned between Close and Thank per JRNL-07"
  - "Instant stage toggle via checkbox click auto-creates stage event per JRNL-08"
  - "STAGES_BEFORE_DECISION / STAGES_AFTER_DECISION grid layout constants"
affects: [journal-grid, stage-events, pipeline-stages]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Split stage column arrays for inserting non-checkbox columns", "useCreateStageEvent for instant toggle with default event types"]

key-files:
  created: []
  modified:
    - frontend/src/pages/journals/components/JournalGrid.tsx
    - frontend/src/pages/journals/components/StageCell.tsx

key-decisions:
  - "Split PIPELINE_STAGES into STAGES_BEFORE_DECISION and STAGES_AFTER_DECISION instead of filtering"
  - "Removed transition warning toasts for independent stage toggles per JRNL-08"
  - "Default event types: contact=call_logged, meet=meeting_completed, close=ask_made, decision=decision_received, thank=thank_you_sent, next_steps=next_step_created"

patterns-established:
  - "Grid column reordering via split stage arrays with non-stage columns inserted between"
  - "Instant toggle pattern: unchecked=auto-create, checked=open detail drawer"

requirements-completed: [JRNL-07, JRNL-08]

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 40 Plan 02: Grid Column Reorder & Instant Stage Toggle Summary

**Decision column repositioned between Close and Thank, stage checkboxes auto-create events on click without opening dialogs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T19:43:49Z
- **Completed:** 2026-02-27T19:46:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Decision column now sits between Close and Thank in the grid, matching the natural pipeline flow (Contact > Meet > Close > Decision > Thank > Next Steps)
- Clicking an unchecked stage checkbox immediately creates a stage event with a sensible default event type -- no dialog or confirmation
- Clicking a checked stage checkbox opens the EventTimelineDrawer for viewing/managing event details
- Loading spinner shown while stage event mutation is in flight
- Independent toggles -- checking any stage does not auto-check earlier stages

## Task Commits

Each task was committed atomically:

1. **Task 1: Reorder grid columns -- Decision between Close and Thank** - `2f17313` (feat)
2. **Task 2: Instant stage toggle -- checkbox click auto-creates event** - `ba57d70` (feat)

**Plan metadata:** (pending) (docs: complete plan)

## Files Created/Modified
- `frontend/src/pages/journals/components/JournalGrid.tsx` - Reordered columns with STAGES_BEFORE_DECISION/STAGES_AFTER_DECISION, Decision card between Close and Thank, journalContactId passed to StageCell
- `frontend/src/pages/journals/components/StageCell.tsx` - Instant toggle behavior: unchecked=auto-create event, checked=open drawer, loading spinner, default event type mapping

## Decisions Made
- Split PIPELINE_STAGES into two local constants (STAGES_BEFORE_DECISION, STAGES_AFTER_DECISION) rather than filtering -- cleaner, explicit column ordering
- Removed transition warning toasts (checkStageTransition) since JRNL-08 specifies independent toggles with no sequential enforcement
- Used journal_contact (not contact_id) in createEvent payload to avoid triggering auto-journal-creation flow in the serializer
- Chose sensible default event types per stage (e.g., call_logged for contact, meeting_completed for meet, ask_made for close)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Grid column reorder and instant toggle are complete
- Journal report backend/frontend changes from plan 01 are still pending commit (pre-existing unstaged changes)
- Phase 40 plan 02 is ready; phase completion depends on plan 01 status

## Self-Check: PASSED

All files and commits verified:
- FOUND: JournalGrid.tsx
- FOUND: StageCell.tsx
- FOUND: SUMMARY.md
- FOUND: 2f17313 (Task 1)
- FOUND: ba57d70 (Task 2)

---
*Phase: 40-journal-report-grid-behavior*
*Completed: 2026-02-27*
