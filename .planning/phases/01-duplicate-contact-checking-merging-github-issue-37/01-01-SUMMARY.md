---
phase: 01-duplicate-contact-checking-merging-github-issue-37
plan: 01
subsystem: database
tags: [pg_trgm, trigram_similarity, contact_merge, duplicate_detection, postgresql]

# Dependency graph
requires: []
provides:
  - DismissedDuplicate model with canonical pair ordering and unique constraint
  - ContactMergeLog audit trail model with survivor/loser snapshot
  - Contact.is_merged and Contact.merged_into fields for soft-delete merge tracking
  - pg_trgm extension via TrigramExtension migration
  - find_duplicates_for_contact service (3-tier confidence scoring)
  - scan_duplicates_for_owner service (batch duplicate scan)
  - merge_contacts service (atomic FK reassignment for all 6 FK types)
affects: [01-02, 01-03, 01-04, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: [django.contrib.postgres, pg_trgm]
  patterns: [soft-delete merge with merged_into FK, canonical pair ordering for dedup, graceful degradation on SQLite for pg_trgm functions]

key-files:
  created:
    - apps/contacts/services.py
    - apps/contacts/migrations/0009_add_pg_trgm_and_merge_models.py
    - apps/contacts/tests/test_merge.py
    - apps/contacts/tests/test_duplicate_detection.py
  modified:
    - config/settings/base.py
    - apps/contacts/models.py

key-decisions:
  - "Clear unique-constrained fields (email) on loser before saving survivor during field overrides to avoid UNIQUE constraint violations"
  - "TrigramSimilarity wrapped in try/except for graceful SQLite degradation in tests -- exact email/phone matching remains SQLite-safe"
  - "Canonical pair ordering (min/max UUID string comparison) used in both DismissedDuplicate.save() and scan_duplicates_for_owner for consistent dedup"

patterns-established:
  - "Soft-delete merge pattern: is_merged=True + merged_into FK, never hard-delete merged contacts"
  - "Graceful degradation pattern: pg_trgm features wrapped in try/except with SQLite fallback"
  - "Canonical pair ordering: (min(str(a_id), str(b_id)), max(...)) for bidirectional pair dedup"

requirements-completed: [DUP-02, DUP-03, DUP-04, DUP-05, DUP-06, DUP-07, DUP-08]

# Metrics
duration: 7min
completed: 2026-03-27
---

# Phase 01 Plan 01: Backend Foundation for Duplicate Contact Detection and Merging Summary

**pg_trgm-powered duplicate detection with 3-tier confidence scoring and atomic contact merge handling all 6 FK relationship types including JournalContact conflict resolution**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-27T21:37:43Z
- **Completed:** 2026-03-27T21:45:17Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Data models for merge tracking: DismissedDuplicate (canonical pair ordering, unique constraint), ContactMergeLog (audit trail with field_overrides and records_migrated JSON), Contact.is_merged/merged_into fields
- Service layer with find_duplicates_for_contact (owner-scoped, exact email/phone + fuzzy trigram name matching, 3-tier confidence), scan_duplicates_for_owner (batch scan excluding dismissed/merged), merge_contacts (atomic transaction with select_for_update)
- Merge handles all 6 FK types: Gift, RecurringGift, Task, PrayerIntention, Event, JournalContact (with unique_together conflict resolution transferring stage events/decisions/next steps)
- 21 passing tests covering merge FK reassignment, group union, soft delete, audit log, field overrides, stats recalculation, and duplicate detection with dismissal tracking

## Task Commits

Each task was committed atomically:

1. **Task 1: Add django.contrib.postgres, Contact merge fields, DismissedDuplicate and ContactMergeLog models with migration** - `bc78281` (feat)
2. **Task 2 RED: Failing tests for merge and duplicate detection** - `b2e98c1` (test)
3. **Task 2 GREEN: Implement services.py with all 3 functions passing tests** - `1f43b3e` (feat)

## Files Created/Modified
- `config/settings/base.py` - Added django.contrib.postgres to INSTALLED_APPS
- `apps/contacts/models.py` - Added is_merged, merged_into fields; DismissedDuplicate and ContactMergeLog models
- `apps/contacts/migrations/0009_add_pg_trgm_and_merge_models.py` - pg_trgm extension + new models/fields
- `apps/contacts/services.py` - find_duplicates_for_contact, scan_duplicates_for_owner, merge_contacts, _merge_journal_contacts
- `apps/contacts/tests/test_merge.py` - 13 test cases for merge functionality
- `apps/contacts/tests/test_duplicate_detection.py` - 8 test cases for duplicate detection and DismissedDuplicate canonicalization

## Decisions Made
- Clear unique-constrained fields (email) on loser before saving survivor during field overrides to avoid UNIQUE constraint violations on (owner, email)
- TrigramSimilarity features wrapped in try/except for graceful SQLite degradation -- exact email/phone matching tests are fully SQLite-safe
- Canonical pair ordering using string comparison of UUIDs used consistently in DismissedDuplicate.save() and scan_duplicates_for_owner for bidirectional pair deduplication

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UNIQUE constraint violation during field overrides**
- **Found during:** Task 2 (merge_contacts implementation)
- **Issue:** When field_overrides={'email': 'right'} copies loser's email to survivor, both contacts temporarily have the same (owner, email) pair, violating unique_contact_email_per_owner constraint
- **Fix:** Clear unique-constrained fields on loser before saving survivor; added _unique_fields tracking set in merge_contacts
- **Files modified:** apps/contacts/services.py
- **Verification:** test_merge_field_overrides passes
- **Committed in:** 1f43b3e (Task 2 commit)

**2. [Rule 1 - Bug] Fixed test data violating email uniqueness constraint**
- **Found during:** Task 2 (test_duplicate_detection.py)
- **Issue:** Test created two contacts with same owner and same email='same@example.com', violating unique_contact_email_per_owner
- **Fix:** Changed tests to use phone matching instead of email matching for duplicate pair creation
- **Files modified:** apps/contacts/tests/test_duplicate_detection.py
- **Verification:** All 21 tests pass
- **Committed in:** 1f43b3e (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness given existing database constraints. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend foundation complete: models, migration, and service layer ready for API endpoint development (Plan 02)
- pg_trgm extension will be installed on first migration run against PostgreSQL
- All services are importable and tested; API views can call find_duplicates_for_contact, scan_duplicates_for_owner, and merge_contacts directly

## Self-Check: PASSED

All 5 created files verified present. All 3 commit hashes verified in git log.

---
*Phase: 01-duplicate-contact-checking-merging-github-issue-37*
*Completed: 2026-03-27*
