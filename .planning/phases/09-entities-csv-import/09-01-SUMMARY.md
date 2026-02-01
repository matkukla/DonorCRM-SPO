---
phase: 09-entities-csv-import
plan: 01
subsystem: import
tags: [csv, import, contacts, validation, tdd, django]

# Dependency graph
requires:
  - phase: 08-funds-csv-import
    provides: CSV import patterns and validation infrastructure
  - phase: 07-entity-models
    provides: Contact model with owner-scoped external_id constraint
provides:
  - parse_entities_csv function with name splitting and validation
  - import_entities function for Contact upserts using external_id
  - Entity CSV template generator
  - Comprehensive test coverage (30 tests)
affects: [09-02-entities-api, 10-donations-csv-import, 11-pledges-csv-import]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Name splitting logic: last word = last_name, rest = first_name"
    - "update_or_create for upserts with conditional unique constraints"
    - "Owner-scoped external_id for multi-tenant contact imports"

key-files:
  created:
    - apps/imports/tests/test_entity_import.py
  modified:
    - apps/imports/services.py

key-decisions:
  - "Use update_or_create instead of bulk_create with update_conflicts due to conditional unique constraint incompatibility"
  - "Entity name split algorithm: single word names become first_name only with empty last_name"
  - "entity_type column ignored (Contact model has no such field)"

patterns-established:
  - "TDD workflow: RED (failing tests) → GREEN (implementation) → atomic commits"
  - "CSV validation before processing: check headers first to fail fast"
  - "Owner-scoped imports: all contacts belong to uploading user"

# Metrics
duration: 7min
completed: 2026-02-01
---

# Phase 09 Plan 01: Entity Import Services Summary

**Owner-scoped Contact upserts from Entities CSV with intelligent name splitting and formula injection protection**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-01T22:20:47Z
- **Completed:** 2026-02-01T22:27:55Z
- **Tasks:** 3 (TDD: RED → GREEN → Verify)
- **Files modified:** 2

## Accomplishments
- Implemented parse_entities_csv with 22 validation test cases passing
- Implemented import_entities with 8 upsert test cases passing
- Name splitting algorithm: "Mary Jane Smith" → first_name="Mary Jane", last_name="Smith"
- Owner-scoped external_id matching for idempotent imports
- Formula character detection prevents CSV injection attacks

## Task Commits

Each task was committed atomically following TDD pattern:

1. **Task 1: RED - Write failing tests** - `48a801e` (test)
   - 30 comprehensive test cases covering validation and upsert logic
   - Tests fail with ImportError (functions not yet implemented)

2. **Task 2: GREEN - Implement functions** - `0ceeef7` (feat)
   - parse_entities_csv with header validation, name splitting, formula detection
   - import_entities using update_or_create for owner-scoped upserts
   - All 30 tests passing

3. **Task 3: Verify and commit** - No additional commit (verification only)
   - Full import test suite: 76 tests passing
   - No regressions in fund import tests

## Files Created/Modified
- `apps/imports/tests/test_entity_import.py` - 30 comprehensive tests for entity import
- `apps/imports/services.py` - Added parse_entities_csv, import_entities, get_entities_template

## Decisions Made

**D1: Use update_or_create instead of bulk_create with update_conflicts**
- **Rationale:** Contact model has conditional unique constraints (`condition=~Q(external_id='')`) which create partial unique indexes. PostgreSQL's ON CONFLICT doesn't work with Django's bulk_create when using partial indexes with WHERE clauses.
- **Alternative considered:** bulk_create with update_conflicts=True, unique_fields=['owner', 'external_id']
- **Issue encountered:** "there is no unique or exclusion constraint matching the ON CONFLICT specification"
- **Solution:** Individual update_or_create calls provide reliable upsert behavior with conditional constraints
- **Trade-off:** Slightly lower performance for large imports, but correctness guaranteed
- **Future optimization:** Could add bulk operations in Phase 10 if performance testing reveals bottleneck

**D2: Entity name split algorithm**
- **Rule:** Last word of name becomes last_name, everything else becomes first_name
- **Edge case:** Single word names (e.g., "Madonna") → first_name="Madonna", last_name=""
- **Rationale:** Matches common CSV export format from SPO and other systems

**D3: entity_type column ignored**
- **Reason:** Contact model has no entity_type field
- **Behavior:** Column is silently ignored during parsing (no error)
- **Future:** If entity_type needed, would require Contact model migration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed email length validation order**
- **Found during:** Task 2 (Implementation)
- **Issue:** Email validation was checking format before length, causing invalid emails that were too long to pass through format validation first
- **Fix:** Reordered validation to check length (254 chars) before format validation
- **Files modified:** apps/imports/services.py
- **Verification:** test_email_exceeds_max_length_returns_error now passes
- **Committed in:** 0ceeef7 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed test: email length validation calculation**
- **Found during:** Task 2 (Test execution)
- **Issue:** Test used 'a' * 245 + '@test.com' = 254 characters (exactly max, not exceeding)
- **Fix:** Changed to 'a' * 246 + '@test.com' = 255 characters (exceeds 254 limit)
- **Files modified:** apps/imports/tests/test_entity_import.py
- **Verification:** Test now correctly validates error case
- **Committed in:** 0ceeef7 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct validation behavior. No scope creep.

## Issues Encountered

**Issue 1: Django bulk_create with conditional unique constraints**
- **Problem:** PostgreSQL ON CONFLICT doesn't work with partial unique indexes created by Django's UniqueConstraint with condition parameter
- **Investigation:** Attempted unique_fields=['owner', 'external_id'] and ['owner_id', 'external_id'] - both failed
- **Root cause:** Partial index has WHERE clause, ON CONFLICT can't reference it without also specifying WHERE in SQL
- **Solution:** Switched to update_or_create which uses standard INSERT...ON CONFLICT or UPDATE logic
- **Outcome:** All tests pass, correctness verified

**Issue 2: Test database constraint creation**
- **Problem:** Initial tests failed because test database didn't have unique constraints
- **Investigation:** Checked production DB had constraints, test DB missing them
- **Root cause:** Tests create fresh database from migrations each run - constraints were present
- **Actual issue:** Was attempting to use bulk_create incorrectly (see Issue 1)
- **Resolution:** Fixed by switching to update_or_create

## Next Phase Readiness

**Ready for 09-02: Entity Import API Endpoint**
- parse_entities_csv and import_entities functions fully tested and working
- Import patterns established and consistent with Phase 8 (Funds import)
- Owner-scoped imports ensure multi-tenant data isolation
- CSV injection protection via formula character detection

**Performance consideration for Phase 10:**
- import_entities uses update_or_create (one query per record)
- For 100+ row imports, may want to profile vs bulk_create alternatives
- Could investigate bulk operations with explicit SQL if needed
- MVP approach prioritizes correctness over optimization

**No blockers.** Ready to wire up API endpoint.

---
*Phase: 09-entities-csv-import*
*Completed: 2026-02-01*
