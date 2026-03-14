---
phase: 50-goal-page-frontend-ui
plan: "01"
subsystem: api
tags: [django, goals, journals, event-sourcing, pytest]

# Dependency graph
requires:
  - phase: 49-goal-backend
    provides: get_goal_progress() service function and GoalJournalSelection model
  - phase: journals
    provides: JournalStageEvent model with event_type choices (call_logged, meeting_completed)
provides:
  - get_goal_progress() extended with calls_count and meetings_count in both return paths
  - GET /api/v1/goals/me/ response now includes calls_count (int) and meetings_count (int)
  - Integration tests for event-sourced activity counts and supervisor GET access
affects:
  - 50-02 through 50-05 (Goal page frontend plans that consume these API fields)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Event-sourced activity counts via JournalStageEvent.objects.filter(journal_contact__journal_id__in=...).count()"
    - "Both return paths (early-return and full-calculation) must be extended when adding new computed fields"

key-files:
  created: []
  modified:
    - apps/users/goal_services.py
    - apps/users/tests/test_views_goals.py

key-decisions:
  - "JournalStageEvent links to JournalContact (not Journal directly), so query uses journal_contact__journal_id__in not journal_id__in"
  - "Early-return path (no journals selected) returns calls_count=0 and meetings_count=0 explicitly"
  - "No fixture factories for JournalStageEvent tests — used direct ORM calls (JournalStageEvent.objects.create)"

patterns-established:
  - "JournalStageEvent query pattern: filter(journal_contact__journal_id__in=selected_journal_ids, event_type='call_logged').count()"

requirements-completed: [GOAL-06, GOAL-10]

# Metrics
duration: 1min
completed: 2026-03-14
---

# Phase 50 Plan 01: Goal API Event-Sourced Activity Counts Summary

**Extended get_goal_progress() to return calls_count and meetings_count from JournalStageEvent records, enabling the frontend Goal page to display read-only activity progress bars.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-14T01:14:04Z
- **Completed:** 2026-03-14T01:15:25Z
- **Tasks:** 1 (TDD)
- **Files modified:** 2

## Accomplishments
- Added `calls_count` and `meetings_count` to both return paths of `get_goal_progress()` in `goal_services.py`
- Counts query `JournalStageEvent` via `journal_contact__journal_id__in` (correct traversal through the FK chain)
- Three new integration tests: presence of keys, count accuracy with real events, supervisor GET returns 200
- All 14 tests pass (5 pre-existing views + 6 pre-existing services + 3 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend get_goal_progress() with event-sourced call/meeting counts** - `98b8a39` (feat)

## Files Created/Modified
- `apps/users/goal_services.py` - Added JournalStageEvent import; calls_count/meetings_count in both return paths
- `apps/users/tests/test_views_goals.py` - Added test_get_returns_calls_meetings_counts, test_calls_count_reflects_journal_events, test_supervisor_can_get_goal_readonly

## Decisions Made
- JournalStageEvent FK chain is `JournalStageEvent -> JournalContact -> Journal`, so the filter must use `journal_contact__journal_id__in`, not `journal_id__in` as the plan's suggested query pattern assumed. Corrected before writing any code.
- Direct ORM calls used in tests instead of fixtures (no journal_factory / stage_event_factory exist in the project).
- Supervisor GET access is confirmed at the API level; the plan notes read-only enforcement is a UI concern only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected JournalStageEvent query path from journal_id__in to journal_contact__journal_id__in**
- **Found during:** Task 1 (before writing implementation)
- **Issue:** Plan's suggested query `JournalStageEvent.objects.filter(journal_id__in=...)` is incorrect — JournalStageEvent has no direct `journal` FK; it links through `journal_contact` (JournalContact model)
- **Fix:** Used `journal_contact__journal_id__in=selected_journal_ids` in both count queries
- **Files modified:** apps/users/goal_services.py
- **Verification:** test_calls_count_reflects_journal_events creates real JournalStageEvent records and asserts count==3
- **Committed in:** 98b8a39 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug in plan's suggested query)
**Impact on plan:** Essential correctness fix. The plan's suggested query would have silently returned 0 for all counts. No scope creep.

## Issues Encountered
None — after correcting the query path, all tests passed on first run.

## Next Phase Readiness
- GET /api/v1/goals/me/ now exposes `calls_count` and `meetings_count` as integers
- Frontend plans (50-02 through 50-05) can consume these fields for progress bars
- No migration needed — no model changes were made

---
*Phase: 50-goal-page-frontend-ui*
*Completed: 2026-03-14*
