# Phase 02: Contact Membership & Search - UAT

## Tests

| # | Test | Status |
|---|------|--------|
| 1 | POST /api/v1/journals/journal-members/ adds a contact to a journal (returns 201) | PASS |
| 2 | DELETE /api/v1/journals/journal-members/{id}/ removes a contact from a journal (returns 204) | PASS |
| 3 | POST with duplicate journal+contact pair returns 400 (not 500) | PASS |
| 4 | GET /api/v1/journals/journal-members/?journal_id=X lists only contacts in that journal | PASS |
| 5 | GET with ?search=<name> filters contacts by name (case-insensitive) | PASS |
| 6 | GET with ?contact__status=<status> filters contacts by status | PASS |

## Results

Started: 2026-01-24
Completed: 2026-01-24
Status: ALL PASS (6/6)

### Verification Method

Ran automated test suite (`apps.journals.tests.test_journal_members`) — 16 tests, all passing:

```
Ran 16 tests in 11.933s
OK
```

### Test Coverage Mapping

| UAT Test | Automated Tests Covering It |
|----------|----------------------------|
| 1 (add contact) | test_add_contact_to_journal_success, test_add_multiple_contacts |
| 2 (remove contact) | test_remove_contact_from_journal |
| 3 (duplicate → 400) | test_duplicate_membership_returns_400 |
| 4 (list by journal) | test_list_with_journal_id_filter |
| 5 (search by name) | test_search_by_first_name, test_search_by_email, test_search_case_insensitive |
| 6 (filter by status) | test_filter_by_contact_status, test_filter_and_search_combined |

### Additional Coverage (ownership/security)

- test_cannot_add_contact_owned_by_other_user
- test_cannot_add_to_journal_owned_by_other_user
- test_cannot_list_other_users_memberships
- test_cannot_delete_other_users_membership
- test_contact_in_multiple_journals
- test_archived_journal_memberships_excluded
