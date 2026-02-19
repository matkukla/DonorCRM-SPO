---
phase: 24-smartsheet-import-backend
plan: 02
subsystem: api
tags: [django, rest-api, csv, xlsx, openpyxl, mpd, smartsheet, import, parsing]

# Dependency graph
requires:
  - phase: 24-01-smartsheet-import-backend
    provides: "MPDUpload and MPDSnapshot models, openpyxl dependency"
  - phase: 06-import-infrastructure
    provides: "imports app with base models and TimeStampedModel"
provides:
  - "MPD import service layer (parsing, matching, snapshot creation) in mpd_services.py"
  - "MPDImportView API endpoint at POST /api/v1/imports/mpd/"
  - "File format auto-detection (CSV/XLSX from magic bytes)"
  - "Formula injection sanitization for imported cell values"
affects: [25-smartsheet-import-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [magic-bytes file format detection, bulk_create with IntegrityError fallback, case-insensitive user matching by first+last name]

key-files:
  created:
    - apps/imports/mpd_services.py
  modified:
    - apps/imports/views.py
    - apps/imports/urls.py

key-decisions:
  - "No file extension check on upload -- format auto-detected from PK magic bytes (XLSX) or fallback (CSV)"
  - "Duplicate user names treated as ambiguous and added to unmatched list (not matched to either)"
  - "Formula injection strips =, +, @, tab, CR but NOT - (negative currency is legitimate)"

patterns-established:
  - "Magic bytes detection: PK\\x03\\x04 = XLSX, else CSV"
  - "Currency parsing: handles $X,XXX.XX, -$X, ($X), None, empty, and numeric types from openpyxl"
  - "Percentage heuristic: abs(value) <= 10 means fractional (multiply by 100), else raw integer"

# Metrics
duration: 3min
completed: 2026-02-19
---

# Phase 24 Plan 02: Service Layer & API Endpoint Summary

**MPD import service with CSV/XLSX parsing, case-insensitive user matching, currency/boolean/percentage parsing, and REST endpoint at POST /api/v1/imports/mpd/**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-19T15:35:24Z
- **Completed:** 2026-02-19T15:38:59Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created mpd_services.py with 12 functions covering file detection, sanitization, currency/boolean/percentage/months parsing, column mapping, row parsing, user matching, and orchestration
- Created MPDImportView with admin-only permissions accepting CSV/XLSX uploads at POST /api/v1/imports/mpd/
- End-to-end verified with sample Smartsheet CSV: 11 rows parsed, all financial fields correctly parsed (Joe Man's active_recurring_gifts = 3085.00, pct_standard_to_max = 104, met_mpd_standard = True), Simon Peter's months_remaining_rf = 'infinite', Mary Grace's months_remaining_rf = '0'

## Task Commits

Each task was committed atomically:

1. **Task 1: Create mpd_services.py with file parsing, user matching, and snapshot creation logic** - `1327b25` (feat)
2. **Task 2: Create MPDImportView API endpoint with URL routing** - `9081f86` (feat)

## Files Created/Modified
- `apps/imports/mpd_services.py` - MPD import service: 12 functions for parsing, matching, snapshot creation
- `apps/imports/views.py` - Added MPDImportView class and process_mpd_upload import
- `apps/imports/urls.py` - Added MPDImportView URL pattern at mpd/

## Decisions Made
- No file extension validation -- format is auto-detected from magic bytes (PK header = XLSX, else CSV), matching CONTEXT.md design
- Duplicate user names in database treated as ambiguous and reported as unmatched (safer than guessing)
- Formula injection characters stripped from start of strings, but NOT the minus sign (negative currency like -$468.33 is legitimate data)
- Percentage heuristic: values with abs <= 10 are treated as fractional and multiplied by 100 (handles both CSV "104%" strings and XLSX 1.04 floats)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend is fully ready for Phase 25 frontend to build the upload UI
- POST /api/v1/imports/mpd/ accepts multipart file upload and returns structured JSON with upload_id, counts, and unmatched row details
- All 5 phase requirements (IMP-01 through IMP-05) are satisfied by the backend

## Self-Check: PASSED

All files verified present. Commits 1327b25 and 9081f86 verified in git log.

---
*Phase: 24-smartsheet-import-backend*
*Completed: 2026-02-19*
