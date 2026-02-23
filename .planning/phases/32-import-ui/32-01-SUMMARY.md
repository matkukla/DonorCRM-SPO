---
phase: 32-import-ui
plan: 01
subsystem: api
tags: [rest-api, react-query, typescript, django, imports]

# Dependency graph
requires:
  - phase: 27-v2-models
    provides: ImportBatch model with SHA256 dedup
  - phase: 28-re-import-solicitor-constituent
    provides: RE solicitor and constituent import endpoints
  - phase: 29-re-import-gift-recurring
    provides: RE gift and recurring gift import endpoints
provides:
  - ImportBatchListView backend endpoint (GET /api/v1/imports/batches/)
  - REImportResponse and ImportBatchRecord TypeScript types
  - importRE() API function for all 4 RE import types
  - getImportBatches() API function with optional type filter
  - useREImport mutation hook with cache invalidation
  - useImportBatches query hook with 30s staleTime
affects: [32-import-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [RE import endpoint mapping via typed Record, ImportBatch list endpoint with select_related]

key-files:
  created: []
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py
    - frontend/src/api/imports.ts
    - frontend/src/hooks/useImports.ts

key-decisions:
  - "No serializer class for ImportBatchListView -- hand-built dict for simplicity (only 12 fields)"

patterns-established:
  - "RE import type mapping: REImportType union -> RE_IMPORT_ENDPOINTS Record for endpoint routing"

requirements-completed: [UI-IMP-06, UI-IMP-03]

# Metrics
duration: 2min
completed: 2026-02-23
---

# Phase 32 Plan 01: API Layer Summary

**ImportBatch list endpoint + typed RE import API functions and React Query hooks for all 4 RE import types**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T20:00:58Z
- **Completed:** 2026-02-23T20:02:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- ImportBatchListView backend endpoint serving recent import history with optional type filtering
- Full TypeScript API layer with REImportResponse, ImportBatchRecord types and importRE/getImportBatches functions
- useREImport mutation hook with automatic cache invalidation for contacts, gifts, and recurringGifts
- useImportBatches query hook with 30s staleTime for import history display

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ImportBatchListView backend endpoint** - `cc9639d` (feat)
2. **Task 2: Add RE import and ImportBatch frontend API layer** - `8209024` (feat)

## Files Created/Modified
- `apps/imports/views.py` - Added ImportBatchListView with admin-only access, select_related, optional import_type filter
- `apps/imports/urls.py` - Added batches/ URL pattern and ImportBatchListView import
- `frontend/src/api/imports.ts` - Added REImportType, REImportResponse, ImportBatchRecord types, importRE() and getImportBatches() functions
- `frontend/src/hooks/useImports.ts` - Added useREImport mutation hook and useImportBatches query hook

## Decisions Made
- No serializer class for ImportBatchListView -- hand-built dict keeps the view self-contained for a simple list endpoint with 12 flat fields

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend endpoint and frontend API layer ready for Import UI page rewrite in Plan 02
- All existing SPO and legacy import functions preserved (additive changes only)

---
*Phase: 32-import-ui*
*Completed: 2026-02-23*
