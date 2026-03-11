---
status: complete
phase: 47-fix-coach-role-gaps
source: [47-01-SUMMARY.md, 47-02-SUMMARY.md]
started: 2026-03-11T00:00:00Z
updated: 2026-03-11T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Role Vocabulary — No IntegrityError
expected: Run the contacts, users, imports, and insights test suites. All tests that previously failed due to role='staff' (stale vocabulary) now pass. No IntegrityError or ValueError mentioning unknown role 'staff' appears in test output.
result: pass

### 2. Coach Can Read Contacts (GET returns 200)
expected: A user with role='coach' can call GET /api/v1/contacts/ and receive a 200 response (not 403). This is verifiable by running the test suite: test_coach_can_list_contacts passes.
result: pass

### 3. Coach Cannot Write Contacts (POST returns 403)
expected: A user with role='coach' attempting POST /api/v1/contacts/ receives 403. Write operations are blocked for coaches. Verifiable via test_coach_cannot_create_contact passing.
result: pass

### 4. Coach Contact List Is Scoped to Their Missionaries
expected: When a coach calls GET /api/v1/contacts/, they only see contacts belonging to missionaries assigned to them — not all contacts in the system. Verifiable via test_coach_contact_list_scoped_to_missionaries passing.
result: pass

### 5. Admin Can Assign Missionaries to a Coach
expected: An admin can PATCH a user with coached_user_ids to assign missionaries to a coach. The M2M relationship persists (verified by re-fetching). Verifiable via test_admin_can_set_coached_user_ids passing.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
