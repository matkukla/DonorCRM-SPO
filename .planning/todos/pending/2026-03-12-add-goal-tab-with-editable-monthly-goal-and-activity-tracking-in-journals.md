---
created: 2026-03-12T14:35:04.802Z
title: Add Goal tab with editable monthly goal and activity tracking in journals
area: ui
files:
  - frontend/src/pages/journals/JournalDetail.tsx
  - frontend/src/pages/journals/components/JournalHeader.tsx
  - apps/journals/models.py
  - apps/journals/serializers.py
  - apps/journals/views.py
---

## Problem

The journal feature currently has no dedicated "Goal" tab. Monthly contact/meeting goals live in settings instead of being visible and editable in context within the journal itself. Users have no way to see at a glance how many phone calls and meetings they have completed vs. how many are needed to hit their monthly goal.

## Solution

Add a "Goal" tab to the journal detail page (`JournalDetail.tsx` tabs section) with:

1. **Editable monthly goal** — move the monthly goal field out of settings and into this tab. Display it prominently with an inline edit affordance (click to edit, save on blur/enter).

2. **Activity tracking dashboard** — visually rich tracking of:
   - Phone calls completed this month vs. goal
   - Meetings completed this month vs. goal
   - Progress bars or ring charts showing % complete
   - Count of remaining calls/meetings needed to hit the monthly target

3. **Design** — clean, beautiful, card-based layout. Use shadcn/ui `Card`, `Progress`, and `Badge` components. Consider a ring/donut chart for visual impact. Color-code: green when on track, amber when behind, red when significantly behind.

**Data source:** Stage events of type `call_logged` and `meeting_completed` (or `meeting_scheduled`/`meeting_completed`) aggregated per month from `JournalStageEvent`. Backend may need a new aggregation endpoint or the frontend can compute from existing member data.

**Monthly goal storage:** Add a `monthly_contact_goal` (integer, calls) and `monthly_meeting_goal` (integer, meetings) field to the `Journal` model, or use a separate `JournalGoal` model for extensibility.
