# Phase 01: Foundation & Data Model - UAT

## Tests

| # | Test | Status |
|---|------|--------|
| 1 | POST /api/v1/journals/ creates a journal with name, goal_amount, and deadline | PASS |
| 2 | PATCH /api/v1/journals/{id}/ updates journal name or goal_amount | PASS |
| 3 | DELETE /api/v1/journals/{id}/ archives the journal (is_archived=True, not hard deleted) | PASS |
| 4 | GET /api/v1/journals/ returns only the authenticated user's journals (archived excluded by default) | PASS |
| 5 | POST /api/v1/journals/stage-events/ creates an append-only stage event with timestamp | PASS |
| 6 | Creating a journal triggers a JOURNAL_CREATED event in the events table | PASS |

## Results

Started: 2026-01-24
Completed: 2026-01-24
Status: ALL PASS (6/6)

### Test Details

1. **Create journal** - POST returns 201, journal has UUID id, correct name/goal_amount/deadline
2. **Update journal** - PATCH returns 200, name updated to new value, goal_amount updated
3. **Archive journal** - DELETE returns 204, is_archived=True, archived_at set, record still exists in DB
4. **Owner scoping** - GET returns 200, archived journals excluded from default list
5. **Stage event** - POST returns 201, stage=contact, event_type=call_logged, created_at timestamp present
6. **Event signal** - Journal.objects.create fires signal, Event with type=JOURNAL_CREATED and title="Journal created: {name}" exists

### Bonus: Stage Event Signal

Creating a stage event also fires the JOURNAL_STAGE_EVENT signal correctly:
- Event title: "Contact: Call Logged" (stage display: event type display)
