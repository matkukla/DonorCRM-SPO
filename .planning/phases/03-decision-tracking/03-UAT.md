---
status: complete
phase: 03-decision-tracking
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-01-24T23:20:00Z
updated: 2026-01-24T23:22:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Create a Decision via API
expected: POST /api/v1/journals/decisions/ with journal_contact, amount, cadence, status returns 201 with created decision including monthly_equivalent field.
result: pass

### 2. Update Decision Creates History
expected: PATCH /api/v1/journals/decisions/{id}/ with a new amount returns 200. A DecisionHistory record is created with the OLD value stored in changed_fields.
result: pass

### 3. Monthly Equivalent Calculation
expected: Creating decisions with different cadences shows correct monthly_equivalent: monthly 100→100.00, quarterly 300→100.00, annual 1200→100.00, one_time 500→0.00.
result: pass

### 4. Paginated Decision History
expected: GET /api/v1/journals/decision-history/?decision_id={id} returns paginated results with default page_size=25. Response includes 'count', 'next', 'previous', and 'results' fields.
result: pass

### 5. Unique Constraint Enforcement
expected: Creating a second decision for the same journal_contact returns 400 with message containing 'already exists'. Different contacts in the same journal can each have their own decision.
result: pass

### 6. Ownership Isolation
expected: User B cannot list, create, or update decisions belonging to User A's journals. GET returns empty results, POST returns 400, PATCH returns 404.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
