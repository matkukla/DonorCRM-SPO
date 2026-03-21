---
created: 2026-03-21T03:16:02.649Z
title: Add scheduled column to journal pipeline
area: ui
files:
  - apps/journals/models.py
  - apps/journals/views.py
  - apps/journals/serializers.py
  - apps/users/goal_services.py
  - apps/insights/services.py
  - frontend/src/types/journals.ts
  - frontend/src/pages/journals/
  - prompts/scheduled_column_prompt.md
---

## Problem

The journal pipeline currently has 6 stages (Contact → Meet → Close → Decision → Thank → Next Steps) but is missing a "Scheduled" stage between Contact and Meet. This stage represents "a meeting has been scheduled with this donor" — an important intermediate step in the fundraising workflow that currently has no tracking mechanism.

Missionaries need to log when a meeting has been scheduled (with date/time), see it as a distinct column in the journal grid, and have it appear in analytics — without affecting goal metrics.

## Solution

Full implementation spec is in `prompts/scheduled_column_prompt.md`. Key changes:

**Backend:**
- Add SCHEDULED stage between Contact and Meet in stage choices
- Add meeting_scheduled event type
- Add nullable JSONField for metadata (scheduled_date, scheduled_time) on JournalStageEvent
- Migration, serializer updates, metadata validation for scheduled stage
- Verify goal_services.py exclusion of new stage from call/meeting counts

**Frontend:**
- Add "Scheduled" to ordered stage list constant (between Contact and Meet)
- Journal grid shows 7 columns: Contact → Scheduled → Meet → Close → Decision → Thank → Next Steps
- Event logging dialog with date picker (required), time picker (optional), notes
- Calendar/clock icon in cell after event logged, optional date label
- Event timeline/drawer shows scheduled events with date/time
- Analytics include Scheduled stage in per-stage displays
