---
status: complete
phase: 49-goal-page-data-model-backend
source: 49-01-SUMMARY.md, 49-02-SUMMARY.md, 49-03-SUMMARY.md, 49-04-SUMMARY.md
started: 2026-03-12T12:00:00Z
updated: 2026-03-12T12:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. All TDD tests pass GREEN
expected: Run: pytest apps/core/tests/test_fiscal_year.py apps/users/tests/test_goal_services.py apps/users/tests/test_views_goals.py — all 17 tests collect and pass with 0 failures and 0 errors.
result: pass

### 2. GET /api/v1/goals/me/ returns correct fields
expected: Authenticated GET request to /api/v1/goals/me/ returns a JSON response containing all 6 keys: monthly_support_goal_cents, goal_weeks, selected_journal_ids, effective_monthly_support, recurring_monthly, one_time_monthly.
result: pass

### 3. PATCH /api/v1/goals/me/ updates goal settings
expected: PATCH request with {"monthly_support_goal_cents": 500000, "goal_weeks": 48} updates the current user's goal fields. Subsequent GET returns the updated values.
result: pass

### 4. PATCH /api/v1/goals/me/ replaces journal selections atomically
expected: PATCH with {"selected_journal_ids": ["<uuid1>", "<uuid2>"]} replaces all existing journal selections. A second PATCH with {"selected_journal_ids": ["<uuid1>"]} leaves only uuid1 selected — uuid2 is removed.
result: pass

### 5. Auth guard rejects unauthenticated requests
expected: GET /api/v1/goals/me/ without authentication returns HTTP 401 or 403. The endpoint is not publicly accessible.
result: pass

### 6. User model has new fields
expected: In Django shell or admin, a User instance has .monthly_support_goal_cents (integer, default 0) and .goal_weeks (integer, default 52) attributes. .monthly_support_goal_dollars returns the cents value divided by 100 as a Decimal.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
