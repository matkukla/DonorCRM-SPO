---
phase: quick
plan: 260323-cnr
subsystem: goals, journals
tags: [decisions, progress-bar, inline-edit, goal-tracking]
dependency_graph:
  requires: [get_goal_progress, GoalView, GoalPage, JournalHeader]
  provides: [get_decisions_progress, decisions-progress-bar, journal-goal-inline-edit]
  affects: [goal-api-response, goal-page-ui, journal-header-ui]
tech_stack:
  added: []
  patterns: [service-function, api-extension, inline-edit-pattern]
key_files:
  created: []
  modified:
    - apps/users/goal_services.py
    - apps/users/views_goals.py
    - apps/users/tests/test_goal_services.py
    - frontend/src/api/goals.ts
    - frontend/src/pages/goal/GoalPage.tsx
    - frontend/src/pages/journals/components/JournalHeader.tsx
decisions:
  - "One-time decisions use /12 multiplier (not model property's 0 multiplier) per GH-26 spec"
  - "Decisions bar uses colorVariant=default (blue) to differentiate from support bar"
  - "noJournalGoals is a separate empty state distinct from emptyState for decisions-specific messaging"
metrics:
  duration: 336s
  completed: "2026-03-23T14:17:54Z"
  tasks: 2
  files_modified: 6
---

# Quick Task 260323-cnr: Add Decisions Progress Bar to Goal Page Summary

Monthly-normalized decision progress bar on Goal page + inline journal goal editing in JournalHeader. Backend service computes one_time/12, monthly*1, quarterly/3, annual/12 for active+pending decisions from selected journals.

## What Was Built

### Backend (Task 1)
- **`get_decisions_progress(user)`** in `apps/users/goal_services.py`: Queries active+pending Decision objects from user's selected journals, computes monthly-normalized sum using correct multipliers (one_time/12 -- NOT the model property which uses 0), sums journal goal_amounts, returns `decisions_current`, `decisions_goal`, `decisions_percentage`
- **GoalView** updated: Both GET and PATCH responses now include the three decisions fields via `data.update(get_decisions_progress(user))`
- **8 new tests** covering: no journals, monthly+one_time, quarterly, annual, declined/paused exclusion, scoping, multi-journal goal sum, API response

### Frontend (Task 2)
- **GoalData interface** extended with `decisions_current`, `decisions_goal`, `decisions_percentage`
- **GoalPage Progress card** now has 4 rows: Monthly Support, Calls, Meetings, Decisions -- with proper empty state messages for no-goal, no-journals, and no-journal-goals
- **JournalHeader** inline-editable goal amount: pencil icon shows edit input, Enter/check saves via PATCH, Escape cancels, hidden in View As mode

## Decisions Made

1. One-time decisions use `/12` multiplier in the service function (not the Decision model's `monthly_equivalent` property which uses `0` for one-time). This matches the GitHub issue specification.
2. Decisions progress bar uses `colorVariant="default"` (blue) to visually differentiate from the Monthly Support bar which uses dynamic color.
3. `noJournalGoals` is computed as a separate state from `emptyState` -- it triggers when user has a main goal and journals selected, but the journal goal_amounts sum to zero.

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

1. `python -m pytest apps/users/tests/test_goal_services.py -x -v --no-cov` -- 14/14 passed
2. `tsc --noEmit` -- no type errors

## Self-Check: PASSED

- All 6 modified files exist on disk
- All 3 commits verified (f3241fd, a09d574, 909e73d)
