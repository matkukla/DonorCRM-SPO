---
phase: 12-import-center-ui
plan: 05
subsystem: backend-api, ui
tags: [django, rest-framework, csv, error-handling, react, typescript]

# Dependency graph
requires:
  - phase: 12-04
    provides: ImportDialog with complete step showing errors
  - phase: 09-02
    provides: ImportRowError model with row_data and error_messages
provides:
  - Backend endpoint GET /api/v1/imports/runs/{id}/errors/csv/ for downloading error CSV
  - Frontend Download Errors CSV button in import summary
  - CSV file with original row data plus error_message column
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSV generation with io.StringIO and csv.DictWriter"
    - "Blob download via responseType: 'blob' and browser download trigger"
    - "Conditional UI rendering based on error_count and import_run_id"

key-files:
  created: []
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py
    - apps/imports/tests/test_views.py
    - frontend/src/api/imports.ts
    - frontend/src/components/imports/ImportDialog.tsx

key-decisions:
  - "CSV error_message column joins multiple errors with semicolon separator"
  - "Filename format: {type}_errors_{run_id}.csv for easy identification"
  - "404 response when no errors exist (better than empty CSV)"
  - "Download button only shows when error_count > 0 AND import_run_id exists"

patterns-established:
  - "Error CSV download pattern for import failures"
  - "Blob download helper reuse for CSV file downloads"
  - "Admin-only permission for error export endpoints"

# Metrics
duration: 2min 54sec
completed: 2026-02-04
---

# Phase 12 Plan 05: Error CSV Download Functionality Summary

**Backend endpoint and frontend button to download CSV of failed import rows with error messages for fixing and re-import**

## Performance

- **Duration:** 2 min 54 sec
- **Started:** 2026-02-04T14:17:33Z
- **Completed:** 2026-02-04T14:20:27Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Created ImportRunErrorsCSVView backend endpoint at GET /api/v1/imports/runs/{id}/errors/csv/
- CSV includes all original row data columns plus error_message column
- Error messages joined with semicolon separator when multiple errors per row
- Admin-only permissions enforced
- Returns 404 if import run not found or has no errors
- Added 4 comprehensive backend tests (success, 404 cases, admin-only)
- Added downloadImportErrorsCSV function to frontend API client
- Added Download Errors CSV button in ImportDialog complete step
- Button conditionally rendered only when error_count > 0 and import_run_id exists
- Frontend build succeeds with no TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ImportRunErrorsCSVView backend endpoint** - `8b46ce7` (feat)
2. **Task 2: Add backend tests for errors CSV endpoint** - `e3601cc` (test)
3. **Task 3: Add frontend download function and button** - `ce4c571` (feat)

## Files Created/Modified

- `apps/imports/views.py` - Added ImportRunErrorsCSVView with CSV generation logic using io.StringIO and csv.DictWriter
- `apps/imports/urls.py` - Added URL route for /runs/{id}/errors/csv/ endpoint
- `apps/imports/tests/test_views.py` - Added TestImportRunErrorsCSVView with 4 test methods
- `frontend/src/api/imports.ts` - Added downloadImportErrorsCSV function with blob download
- `frontend/src/components/imports/ImportDialog.tsx` - Added Download Errors CSV button in complete step

## Decisions Made

### D1: Semicolon separator for multiple errors
**Context:** ImportRowError.error_messages is a list of error strings per row.

**Decision:** Join multiple errors with '; ' separator in error_message CSV column.

**Rationale:** Semicolon is Excel-safe (won't split into columns), human-readable, and allows admin to see all validation errors for a row in single cell. Alternative newline separator would break CSV format.

### D2: Filename format with type and run ID
**Context:** Downloaded CSV needs descriptive filename.

**Decision:** Use format `{type}_errors_{run_id}.csv` (e.g., `funds_errors_8b46ce7.csv`).

**Rationale:** Type helps admin identify which import failed, truncated run_id provides uniqueness without being unwieldy, .csv extension ensures proper handling by OS and Excel.

### D3: 404 when no errors exist
**Context:** What to return when import run exists but has no errors?

**Decision:** Return 404 with message "No errors found for this import run."

**Rationale:** Better UX than empty CSV file (which might confuse admin). Button shouldn't appear unless errors exist, but 404 provides safety if button shown incorrectly. Empty CSV would waste download bandwidth.

### D4: Conditional button rendering
**Context:** When should Download Errors button appear?

**Decision:** Show button only when `error_count > 0 AND import_run_id exists`.

**Rationale:** error_count confirms errors exist (validates button is useful), import_run_id confirms backend has ImportRun record (validates download will work). Both conditions prevent broken download attempts.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks executed as planned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Phase 12 complete - Import Center UI v1.1 milestone ready:**
- All 4 import types have full workflow (upload, preview, validate, import, summary)
- Error handling complete with downloadable CSV for fixing and re-import
- Import status tracking functional (latest runs, dependency warnings)
- CSV preview client-side with react-papaparse
- State machine enforces valid workflow transitions

**No blockers identified.**

## Verification Evidence

```bash
# All import tests passing (including 4 new error CSV tests)
pytest apps/imports/tests/test_views.py -v --no-cov
# Result: 8 passed, 2 warnings in 2.92s

# Frontend build successful
cd frontend && npm run build
# Result: ✓ built in 7.39s

# Download function exists
grep -n "downloadImportErrorsCSV" frontend/src/api/imports.ts
# Result: Line 119 (function definition)

# Download button exists
grep -n "Download Errors" frontend/src/components/imports/ImportDialog.tsx
# Result: Line 384 (button text)
```

## Key Learnings

1. **CSV generation in Django:** io.StringIO + csv.DictWriter pattern is clean and memory-efficient for in-memory CSV generation (no temp files needed)
2. **Blob downloads in React:** apiClient responseType: "blob" with downloadFile helper enables clean file download UX
3. **Conditional rendering safety:** Multiple conditions (error_count > 0 AND import_run_id) prevent broken button states
4. **404 for missing data:** Better than empty response when requested resource legitimately doesn't exist (no errors case)
5. **Error message joining:** Semicolon separator preserves CSV structure while allowing multiple errors per row
6. **Pytest vs Django test runner:** Project uses pytest (test classes don't inherit TestCase), run with `pytest` not `python manage.py test`

---
*Phase: 12-import-center-ui*
*Completed: 2026-02-04*
