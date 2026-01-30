---
phase: 08-funds-csv-import
plan: 01
subsystem: api
tags: [django, csv, validation, bulk-upsert, tdd, pytest]

# Dependency graph
requires:
  - phase: 07-foundation
    provides: Fund model with external_id for upsert, ImportRun and ImportRowError models
provides:
  - parse_funds_csv function with comprehensive validation
  - import_funds function with bulk upsert logic
  - CSV injection prevention for fund imports
  - Test coverage for fund import business logic
affects: [08-02-fund-import-api, 08-03-fund-import-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD workflow: RED (failing tests) → GREEN (implementation) → commit pattern"
    - "CSV injection prevention via formula character detection (=, +, -, @)"
    - "Bulk upsert with bulk_create(update_conflicts=True) for idempotent imports"

key-files:
  created:
    - apps/imports/tests/test_fund_import.py
  modified:
    - apps/imports/services.py

key-decisions:
  - "Status validation is case-insensitive (ACTIVE → active, Closed → closed)"
  - "Status defaults to 'active' when missing from CSV"
  - "Formula character detection prevents CSV injection attacks"
  - "Funds imported with null owner (org-wide by default)"

patterns-established:
  - "TDD pattern: Write comprehensive tests first, implement to pass, commit atomically"
  - "CSV parsing: Validate headers before processing rows to fail fast"
  - "Bulk upsert: Query existing IDs first, calculate created/updated counts"
  - "ImportRun tracking: Update status and counts after successful import"

# Metrics
duration: 4min
completed: 2026-01-30
---

# Phase 8 Plan 01: Fund Import Services Summary

**TDD implementation of fund CSV parsing and bulk upsert with formula injection prevention and case-insensitive status validation**

## Performance

- **Duration:** 4 minutes
- **Started:** 2026-01-30T20:41:41Z
- **Completed:** 2026-01-30T20:45:42Z
- **Tasks:** 3 (TDD: RED → GREEN → verify)
- **Files modified:** 2

## Accomplishments
- Comprehensive CSV parsing with validation for fund imports
- Bulk upsert implementation using Django's bulk_create with conflict resolution
- CSV injection prevention blocking formula characters (=, +, -, @)
- 20 test cases covering validation, error reporting, and import logic
- All tests passing with 100% TDD coverage

## Task Commits

Each task was committed atomically following TDD pattern:

1. **Task 1: RED - Write failing tests for parse_funds_csv** - `7441f9e` (test)
2. **Task 2: GREEN - Implement parse_funds_csv and import_funds** - `fee2849` (feat)

_Note: Tasks 2-3 combined in GREEN phase - both parse_funds_csv and import_funds implemented together to satisfy all 20 tests_

## Files Created/Modified
- `apps/imports/tests/test_fund_import.py` - 20 comprehensive test cases for fund import validation and upsert logic
- `apps/imports/services.py` - Added parse_funds_csv and import_funds functions with validation and bulk upsert

## Decisions Made

**D1: Case-insensitive status validation with normalization**
- Rationale: User-friendly - accepts "ACTIVE", "Active", "active" all as valid
- Implementation: Normalize to lowercase before enum validation
- Valid values: active, inactive, closed

**D2: Status defaults to 'active' when missing**
- Rationale: Reasonable default for new funds, reduces CSV complexity
- CSV column is optional, empty/missing values become 'active'

**D3: Formula character detection for CSV injection prevention**
- Rationale: Security - prevent Excel/Sheets formula injection attacks
- Reject fund_id or name starting with =, +, -, @ characters
- Explicit error message for security awareness

**D4: Funds created with null owner (org-wide)**
- Rationale: Funds are shared resources across organization
- Consistent with 07-01 decision that Fund.owner is nullable for org-wide funds
- Individual fund ownership can be assigned later if needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TDD workflow proceeded smoothly with all tests passing on first GREEN implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 08-02 (Fund Import API):**
- parse_funds_csv and import_funds functions tested and working
- Validation rules established (required fields, max lengths, status enum)
- CSV injection prevention implemented
- Error reporting structure defined (row number, errors list, original data)
- ImportRun status and count tracking implemented

**Considerations for next phase:**
- FundImportView will need to handle file upload and call these service functions
- Error response format should match validation error structure from parse_funds_csv
- Consider rate limiting for import endpoint (SPO sync may be frequent)

---
*Phase: 08-funds-csv-import*
*Completed: 2026-01-30*
