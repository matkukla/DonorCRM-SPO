---
phase: 11-pledges-csv-import
plan: 02
subsystem: csv-import
tags: [django, rest-framework, api, pytest, integration-tests, pledge]

# Dependency graph
requires:
  - phase: 11-01
    provides: parse_pledges_csv, import_pledges, get_pledges_template service functions
  - phase: 10-02
    provides: TransactionImportView API pattern, integration test patterns
  - phase: 09-02
    provides: EntityImportView patterns for owner-scoped FK validation
provides:
  - PledgeImportView API endpoint at /api/v1/imports/pledges/
  - PledgeTemplateView API endpoint at /api/v1/imports/templates/pledges/
  - 18 integration tests covering permissions, validation, and import behavior
affects: [12-import-ui, api-documentation, pledge-import-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - API view pattern without stats update (pledges use computed properties)
    - Optional FK validation with empty string handling in API responses

key-files:
  created: []
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py
    - apps/imports/tests/test_pledge_import.py

key-decisions:
  - "PledgeImportView follows TransactionImportView pattern without update_contact_stats call"
  - "Integration tests verify fund=None when fund_id empty"
  - "Integration tests verify Contact.total_given unchanged after pledge import"

patterns-established:
  - "Optional FK endpoint pattern: validate fund_id only if provided, allow empty"
  - "No denormalized stats update in API layer for computed property entities"

# Metrics
duration: 3m 55s
completed: 2026-02-03
---

# Phase 11 Plan 02: Pledges CSV Import API Summary

**PledgeImportView and PledgeTemplateView API endpoints with 18 integration tests, following TransactionImportView pattern without Contact stats updates**

## Performance

- **Duration:** 3m 55s
- **Started:** 2026-02-03T14:53:23Z
- **Completed:** 2026-02-03T14:57:18Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- PledgeImportView API endpoint at /api/v1/imports/pledges/ with admin-only access, validate_only mode, strict validation, and optional fund_id support
- PledgeTemplateView API endpoint at /api/v1/imports/templates/pledges/ returning CSV template with correct column headers
- 18 comprehensive integration tests (15 for PledgeImportView, 3 for PledgeTemplateView) covering permissions, file validation, FK validation, enum validation, upsert behavior, and stats non-update
- All 202 tests passing across full import suite (Phases 8-11)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PledgeImportView and PledgeTemplateView** - `0b610ce` (feat)
2. **Task 2: Wire URL routes for pledge import** - `e36161c` (feat)
3. **Task 3: Add integration tests for PledgeImportView** - `885f835` (test)

## Files Created/Modified
- `apps/imports/views.py` - Added PledgeImportView and PledgeTemplateView classes following TransactionImportView pattern
- `apps/imports/urls.py` - Added URL routes for /pledges/ and /templates/pledges/ endpoints
- `apps/imports/tests/test_pledge_import.py` - Added 18 integration tests (TestPledgeImportView with 15 tests, TestPledgeTemplateView with 3 tests)

## Decisions Made

**D1: No update_contact_stats_for_import call in PledgeImportView**
- Rationale: Contact pledge stats (has_active_pledge, monthly_pledge_amount) are computed properties that query pledges directly, not denormalized fields
- Implementation: PledgeImportView.post() does NOT call update_contact_stats_for_import after successful import (differs from TransactionImportView)
- Impact: Simpler import logic, documented in view docstring, verified by integration test test_contact_stats_not_updated_after_import
- Traced to: Phase 11-01 Decision D3

**D2: Integration test coverage includes computed property verification**
- Rationale: Ensure pledge import doesn't break Contact computed properties
- Implementation: test_contact_stats_not_updated_after_import verifies Contact.total_given unchanged and Contact.has_active_pledge accessible
- Impact: Documents expected behavior difference from transaction imports for future maintainers

**D3: UTF-8 BOM test uses byte format**
- Rationale: Excel CSV exports include UTF-8 BOM (byte order mark) that must be handled correctly
- Implementation: Test uses `b'\xef\xbb\xbf'` byte prefix instead of string encoding to properly simulate Excel export
- Impact: Ensures utf-8-sig decoding in view works correctly for real-world Excel files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UTF-8 BOM test encoding format**
- **Found during:** Task 3 (test execution)
- **Issue:** test_utf8_bom_handled_correctly used `csv_content.encode('utf-8-sig')` which doesn't produce same BOM as Excel
- **Fix:** Changed to byte format `bom = b'\xef\xbb\xbf'` matching Excel's actual BOM bytes
- **Files modified:** apps/imports/tests/test_pledge_import.py
- **Verification:** Test passes, matches transaction import test pattern
- **Committed in:** 885f835 (Task 3 commit)

**2. [Rule 1 - Bug] Fixed error structure assertion format**
- **Found during:** Task 3 (test execution)
- **Issue:** test_orphan_entity_id_returns_error expected `response.data['errors'][0]['row']` to be string "row 2", but service returns integer 2
- **Fix:** Changed assertion to `assert response.data['errors'][0]['row'] == 2`
- **Files modified:** apps/imports/tests/test_pledge_import.py
- **Verification:** Test passes, matches transaction import error format
- **Committed in:** 885f835 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 test bugs)
**Impact on plan:** Test fixes ensure integration tests match established Phase 8/9/10 patterns. No scope creep.

## Issues Encountered
None - API implementation and tests followed established patterns from Phase 10

## Next Phase Readiness

**Ready for Phase 12 (Import UI):**
- All 4 CSV import API endpoints complete (funds, entities, transactions, pledges)
- Consistent response format across all endpoints (created_count, updated_count, error_count, errors, import_run_id)
- Consistent validation patterns (validate_only mode, strict mode, orphan FK detection)
- Template endpoints return correct column headers for all 4 CSV types
- Full test coverage (202 tests across Phase 8-11 import suite)

**API patterns established:**
- Admin-only access via IsAdmin permission class
- UTF-8-sig decoding for Excel BOM handling
- validate_only dry-run mode for preview
- Strict mode: reject entire import if any validation errors
- ImportRun audit records for successful imports
- Error responses with row numbers and detailed error messages

---
*Phase: 11-pledges-csv-import*
*Completed: 2026-02-03*
