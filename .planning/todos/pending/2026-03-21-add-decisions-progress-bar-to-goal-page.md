---
created: 2026-03-21T03:17:38.210Z
title: Add decisions progress bar to goal page
area: ui
files:
  - apps/journals/models.py
  - apps/users/goal_services.py
  - apps/users/views.py
  - apps/journals/serializers.py
  - frontend/src/pages/goal/GoalPage.tsx
  - frontend/src/hooks/useGoals.ts
  - prompts/progress_bar_prompt.md
---

## Problem

The Goal page tracks support progress but has no visibility into decision progress from journals. Missionaries need to see the combined monthly-equivalent value of committed and pending decisions from their selected journals, measured against each journal's goal amount. There is also no UI for missionaries to set a goal amount on individual journals.

## Solution

Full implementation spec is in `prompts/progress_bar_prompt.md`. Key changes:

**Backend:**
- Ensure Journal.goal_amount field exists and is usable (integer cents, nullable)
- New `get_decisions_progress(user)` service function in goal_services.py
  - Queries decisions (yes + pending status) from selected journals
  - Monthly normalization: monthly as-is, one-time / 12
  - Returns decisions_current, decisions_goal, decisions_percentage
- Extend GET /api/v1/goals/me/ response with the three new fields
- Journal serializer includes goal_amount in read/write

**Frontend:**
- Add "Goal Amount" field to journal edit form (dollar input converting to cents)
- Add "Decisions Progress" bar at bottom of Goal page progress section
  - Same component/styling as existing support progress bar
  - Shows $X / $Y with dollar formatting
  - Helper messages when no goals set or no journals selected
- Extend goal data hook and TypeScript types
- View As: progress bar displays read-only, goal amount field disabled
