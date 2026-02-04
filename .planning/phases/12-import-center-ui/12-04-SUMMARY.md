---
phase: 12-import-center-ui
plan: 04
subsystem: ui
tags: [react, typescript, react-papaparse, shadcn-ui, state-machine, imports]

# Dependency graph
requires:
  - phase: 12-03
    provides: SPOImportTile components with import button handlers
  - phase: 12-02
    provides: react-papaparse dependency installed
  - phase: 12-01
    provides: SPO import API endpoints with validate_only support
provides:
  - ImportDialog component with useReducer state machine for multi-step workflow
  - CSVPreviewTable component for client-side CSV preview
  - Complete import workflow: Upload → Preview → Validate → Import → Summary
affects: [12-05-error-download]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useReducer state machine for multi-step workflow (upload, preview, validating, validated, importing, complete, error)"
    - "react-papaparse useCSVReader hook for client-side CSV parsing"
    - "Validation-gated import button (disabled until error_count === 0)"
    - "API dry-run validation with validate_only=true before import"

key-files:
  created:
    - frontend/src/components/imports/ImportDialog.tsx
    - frontend/src/components/imports/CSVPreviewTable.tsx
  modified:
    - frontend/src/pages/admin/ImportCenter.tsx

key-decisions:
  - "useReducer state machine enforces valid state transitions (prevents invalid workflows)"
  - "Preview shows first 25 rows client-side (balance between preview and performance)"
  - "Import button disabled when validation has errors (prevents failed imports)"
  - "Validation step calls API with validate_only=true (dry-run before real import)"
  - "Cancel button available at all steps with confirmation during import (safe UX)"

patterns-established:
  - "ImportDialog reusable for all 4 import types via importType prop"
  - "CSVPreviewTable with sticky headers and row number column"
  - "State machine pattern for complex multi-step workflows"
  - "Client-side CSV parsing with react-papaparse for instant preview"

# Metrics
duration: 2min 28sec
completed: 2026-02-04
---

# Phase 12 Plan 04: Import Workflow Dialog with State Machine Summary

**Multi-step import dialog with Upload → Preview → Validate → Import → Summary workflow using useReducer state machine, client-side CSV preview via react-papaparse, and validation-gated import button**

## Performance

- **Duration:** 2 min 28 sec
- **Started:** 2026-02-04T14:12:36Z
- **Completed:** 2026-02-04T14:15:04Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created CSVPreviewTable component with sticky headers and row number column
- Implemented ImportDialog with useReducer state machine managing 7 states (upload, preview, validating, validated, importing, complete, error)
- Integrated react-papaparse useCSVReader for client-side CSV parsing
- Validation step calls API with validate_only=true for dry-run
- Import button disabled when validation has errors (error_count > 0)
- Summary step shows created/updated/error counts from import result
- Cancel button available at all steps with confirmation during import
- Wired ImportDialog into ImportCenter replacing placeholder dialog

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CSVPreviewTable component** - `327a7d1` (feat)
2. **Task 2: Create ImportDialog with state machine** - `bd49b67` (feat)
3. **Task 3: Wire ImportDialog into ImportCenter** - `7abcd50` (feat)

## Files Created/Modified

- `frontend/src/components/imports/CSVPreviewTable.tsx` - Table component displaying first 25 CSV rows with sticky headers, row numbers, and truncated cell content
- `frontend/src/components/imports/ImportDialog.tsx` - Multi-step dialog with state machine, file upload, preview, validation, import, and summary steps
- `frontend/src/pages/admin/ImportCenter.tsx` - Replaced placeholder dialog with real ImportDialog component

## Decisions Made

### D1: useReducer state machine for workflow
**Context:** Multi-step import workflow needs to enforce valid state transitions.

**Decision:** Use useReducer with 7 states (upload, preview, validating, validated, importing, complete, error) and 8 actions (UPLOAD_FILE, START_VALIDATION, VALIDATION_SUCCESS, VALIDATION_ERROR, START_IMPORT, IMPORT_SUCCESS, IMPORT_ERROR, RESET).

**Rationale:** State machine pattern prevents invalid state transitions (e.g., can't import before validation passes), makes workflow logic explicit, easier to test and debug than useState with multiple boolean flags.

### D2: Preview first 25 rows client-side
**Context:** Large CSV files could slow down UI if previewing all rows.

**Decision:** Preview only first 25 rows in CSVPreviewTable (configurable via maxRows prop).

**Rationale:** Balance between showing enough data for user to verify file structure and maintaining fast UI performance. 25 rows fits comfortably on screen without scrolling, matches common preview sizes (Excel shows 20-30 rows by default).

### D3: Import button disabled until validation passes
**Context:** Backend rejects imports with validation errors.

**Decision:** Import button disabled when `error_count > 0`, enabled only when `error_count === 0`.

**Rationale:** Prevents users from attempting import when backend will reject it, provides clear visual feedback that validation must pass first, reduces wasted API calls.

### D4: Validation dry-run with validate_only=true
**Context:** Users need to know if file has errors before committing to import.

**Decision:** Validation step calls API with `validate_only=true` query parameter.

**Rationale:** Backend performs full validation without database writes, returns same error structure as real import, allows users to fix file and retry validation multiple times before import.

### D5: Cancel with confirmation during import
**Context:** User might accidentally close dialog during import.

**Decision:** Show window.confirm() if closing dialog during "importing" step, allow cancel without confirmation at all other steps.

**Rationale:** Prevents accidental data loss (import might be partially complete), doesn't annoy users with confirmation when no risk (upload/preview/validated steps).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks executed as planned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Phase 12-05 (Error Download Button) can proceed:**
- ImportDialog complete step shows errors list
- import_run_id available in SPOImportResult
- Error download button placeholder comment present
- Summary step ready for enhancement

**No blockers identified.**

## Verification Evidence

```bash
# Build succeeded with no TypeScript errors
cd frontend && npm run build
# Result: ✓ built in 11.11s

# Components created
ls -la frontend/src/components/imports/ImportDialog.tsx frontend/src/components/imports/CSVPreviewTable.tsx
# Result: Both files exist

# ImportDialog integrated in ImportCenter
grep -n "ImportDialog" frontend/src/pages/admin/ImportCenter.tsx
# Result: Line 8 (import), Line 135 (component usage)
```

## Key Learnings

1. **useReducer for complex workflows:** State machine pattern much cleaner than multiple useState for multi-step flows (prevents invalid states, centralizes transition logic)
2. **react-papaparse useCSVReader:** Provides both file input and parsing in single hook, returns parsed data directly as array of objects (no manual parsing needed)
3. **Client-side CSV preview:** Instant feedback without API call, improves UX for file verification before validation
4. **Validation-gated imports:** Disabling import button based on validation result prevents user errors and wasted API calls
5. **Dialog state persistence:** useReducer state persists across re-renders but resets on close (RESET action on dialog close)
6. **Error handling in mutations:** TypeScript requires explicit type assertion for caught errors (err as { response?: { data?: { detail?: string } } })

---
*Phase: 12-import-center-ui*
*Completed: 2026-02-04*
